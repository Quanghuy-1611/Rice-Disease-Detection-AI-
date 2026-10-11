"""Plus multi-image request: one quota unit for up to five images."""

from pathlib import Path
import uuid

import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.inference_monitor import InferenceBusyError, monitor
from app.api.image_quality import prepare_image, quality_message
from app.api.ipm_advisor import get_ipm_advice
from app.api.plans import active_plan, plan_status, plus_model_ready, refund_request, reserve_request
from app.api.plus_model import plus_model
from app.database import get_db
from app.models import ClientActivity, Diagnosis

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
MAX_BYTES = 10 * 1024 * 1024


def summarize_batch(results: list[dict]) -> tuple[str | None, str | None]:
    """Use consistent high-confidence photos; never force a label from conflicts."""
    accepted = [result["prediction"] for result in results if result["prediction"]]
    required = 1 if len(results) == 1 else 2 if len(results) <= 3 else 3
    if len(accepted) >= required and len(set(accepted)) == 1:
        message = (f"Kết luận từ {len(accepted)}/{len(results)} ảnh đủ chắc chắn; "
                   "các ảnh còn lại cần kiểm tra thêm.") if len(accepted) < len(results) else None
        return accepted[0], message
    return None, "Các ảnh chưa thống nhất hoặc chưa đủ rõ. Không kết luận chung từ bộ ảnh này."


@router.post("/predict/plus")
async def predict_plus(request: Request, files: list[UploadFile] = File(...),
                       severity: str = Form("low"), db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    if not plus_model_ready():
        raise HTTPException(503, "Plus chưa qua kiểm định mô hình; chưa mở chẩn đoán hoặc thu phí.")
    if active_plan(db, current_user) != "plus":
        raise HTTPException(403, "Tài khoản cần gói Plus để phân tích nhiều ảnh.")
    if not 1 <= len(files) <= 5:
        raise HTTPException(422, "Plus nhận từ 1 đến 5 ảnh cho mỗi lượt.")
    if severity not in {"low", "medium", "high"}:
        raise HTTPException(422, "Mức độ chỉ nhận low, medium hoặc high.")
    images = []
    for file in files:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(400, "Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.")
        contents = await file.read(MAX_BYTES + 1)
        if len(contents) > MAX_BYTES:
            raise HTTPException(413, "Mỗi ảnh tối đa 10 MB.")
        try:
            image = prepare_image(contents)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(400, "Có ảnh không hợp lệ.") from exc
        except ValueError as exc:
            raise HTTPException(422, f"Ảnh {len(images) + 1}: {exc}") from exc
        quality_issue = quality_message(image)
        if quality_issue:
            raise HTTPException(422, f"Ảnh {len(images) + 1}: {quality_issue}")
        images.append(image)
    reserved = reserve_request(db, current_user, "plus")
    try:
        predictions = [await monitor.run(plus_model.predict_one, image) for image in images]
    except InferenceBusyError as exc:
        if reserved:
            refund_request(db, current_user, "plus")
        raise HTTPException(503, "Máy chủ đang bận. Vui lòng thử lại sau vài giây.",
                            headers={"Retry-After": "5"}) from exc
    except Exception as exc:
        if reserved:
            refund_request(db, current_user, "plus")
        raise HTTPException(500, "Không thể phân tích bộ ảnh Plus.") from exc
    created_files = []
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        results = []
        for image, prediction in zip(images, predictions):
            image_name = f"{uuid.uuid4().hex}.jpg"
            image_path = UPLOAD_DIR / image_name
            image.save(image_path, format="JPEG", quality=90)
            created_files.append(image_path)
            heatmap_url = None
            heatmap = prediction.pop("heatmap")
            if heatmap is not None and np.max(heatmap) > 0:
                base = np.asarray(image, dtype=np.float32)
                intensity = np.clip((heatmap - .15) / .85, 0, 1)[..., None]
                alpha = .65 * intensity
                overlay = np.uint8(np.clip(base * (1 - alpha) + alpha * np.array([255, 65, 30]), 0, 255))
                heatmap_name = f"{uuid.uuid4().hex}_heatmap.jpg"
                heatmap_path = UPLOAD_DIR / heatmap_name
                Image.fromarray(overlay).save(heatmap_path, format="JPEG", quality=90)
                created_files.append(heatmap_path)
                heatmap_url = f"/uploads/{heatmap_name}"
            db.add(Diagnosis(image_filename=image_name,
                             prediction=prediction["prediction"] or "uncertain",
                             confidence=prediction["confidence"], owner_id=current_user.id))
            results.append({**prediction, "filename": image_name, "heatmap_url": heatmap_url})
        summary, summary_message = summarize_batch(results)
        platform = request.headers.get("X-RiceAI-Client", "unknown").lower()
        if platform not in {"web", "ios", "android"}:
            platform = "unknown"
        db.add(ClientActivity(user_id=current_user.id, platform=platform,
                              app_version=request.headers.get("X-RiceAI-Version", "unknown")[:40],
                              event="diagnosis_plus"))
        db.commit()
    except Exception as exc:
        db.rollback()
        for path in created_files:
            path.unlink(missing_ok=True)
        if reserved:
            refund_request(db, current_user, "plus")
        raise HTTPException(500, "Không thể lưu báo cáo Plus.") from exc
    return {"success": True, "analysis_mode": "plus", "images": results,
            "prediction": summary,
            "message": summary_message,
            "ipm_advice": get_ipm_advice(summary, severity) if summary else None,
            "plan": plan_status(db, current_user)}
