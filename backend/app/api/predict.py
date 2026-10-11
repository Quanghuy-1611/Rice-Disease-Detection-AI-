"""Seven-class prediction API shared by web and mobile clients."""

from __future__ import annotations

from pathlib import Path
import uuid

import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.inference_monitor import InferenceBusyError, monitor
from app.api.image_quality import prepare_image, quality_message
from app.api.ipm_advisor import get_ipm_advice
from app.api.plans import active_plan, plan_status, refund_request, reserve_request
from app.api.seven_class_model import CLASSES, model
from app.database import get_db
from app.models import Diagnosis, ClientActivity

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MIN_CONFIDENCE = 0.95


@router.post("/predict")
async def predict_image(
    request: Request,
    file: UploadFile = File(...),
    severity: str = Form("low"),
    analysis_mode: str = Form("basic"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if analysis_mode != "basic":
        raise HTTPException(status_code=422, detail="Mô hình 7 lớp hiện chỉ hỗ trợ Basic/Grad-CAM.")
    if severity not in {"low", "medium", "high"}:
        raise HTTPException(status_code=422, detail="Mức độ chỉ nhận low, medium hoặc high.")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Vui lòng tải lên tệp hình ảnh.")
    if model.model is None:
        raise HTTPException(status_code=503, detail="Mô hình 7 lớp chưa sẵn sàng.")
    if current_user.email.startswith("guest_") and current_user.email.endswith("@anonymous.riceai"):
        raise HTTPException(status_code=403, detail="Hãy đăng nhập bằng email đã xác minh để chẩn đoán.")
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Ảnh vượt quá giới hạn 10 MB.")
    try:
        image = prepare_image(contents)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Tệp ảnh không hợp lệ.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    quality_issue = quality_message(image)
    if quality_issue:
        raise HTTPException(status_code=422, detail=quality_issue)

    quota_plan = active_plan(db, current_user)
    reserved = reserve_request(db, current_user, quota_plan)

    try:
        predicted_class, confidence, heatmap = await monitor.run(model.predict, image)
    except InferenceBusyError as exc:
        if reserved:
            refund_request(db, current_user, quota_plan)
        raise HTTPException(
            status_code=503,
            detail="Đang có nhiều ảnh chờ phân tích. Vui lòng thử lại sau vài giây.",
            headers={"Retry-After": "5"},
        ) from exc
    except Exception as exc:
        if reserved:
            refund_request(db, current_user, quota_plan)
        raise HTTPException(status_code=500, detail="Không thể phân tích ảnh.") from exc

    uncertain = confidence < MIN_CONFIDENCE
    if uncertain:
        heatmap = None

    created_files = []
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        image_name = f"{uuid.uuid4().hex}.jpg"
        image_path = UPLOAD_DIR / image_name
        image.save(image_path, format="JPEG", quality=90)
        created_files.append(image_path)
        heatmap_url = None
        if heatmap is not None:
            rgb = np.asarray(image, dtype=np.float32)
            intensity = np.clip((heatmap - .15) / .85, 0, 1)[..., None]
            alpha = .65 * intensity
            overlay = np.uint8(np.clip(rgb * (1 - alpha) + alpha * np.array([255, 65, 30]), 0, 255))
            heatmap_name = f"{uuid.uuid4().hex}_heatmap.jpg"
            heatmap_path = UPLOAD_DIR / heatmap_name
            Image.fromarray(overlay).save(heatmap_path, format="JPEG", quality=90)
            created_files.append(heatmap_path)
            heatmap_url = f"/uploads/{heatmap_name}"

        db.add(Diagnosis(image_filename=image_name,
                         prediction="uncertain" if uncertain else predicted_class,
                         confidence=confidence, owner_id=current_user.id))
        platform = request.headers.get("X-RiceAI-Client", "unknown").lower()
        if platform not in {"web", "ios", "android"}:
            platform = "unknown"
        version = request.headers.get("X-RiceAI-Version", "unknown")[:40]
        db.add(ClientActivity(user_id=current_user.id, platform=platform,
                              app_version=version, event="diagnosis"))
        db.commit()
    except Exception as exc:
        db.rollback()
        for path in created_files:
            path.unlink(missing_ok=True)
        if reserved:
            refund_request(db, current_user, quota_plan)
        raise HTTPException(500, "Không thể lưu kết quả chẩn đoán.") from exc
    return {
        "success": True,
        "prediction": None if uncertain else predicted_class,
        "confidence": confidence,
        "uncertain": uncertain,
        "message": "Mô hình chưa đủ chắc chắn trong 7 nhóm hiện có. Hãy chụp lại hoặc nhờ chuyên gia kiểm tra." if uncertain else None,
        "scope_warning": "RiceAI hiện chỉ nhận diện 7 nhóm đã huấn luyện; bệnh hoặc đối tượng khác vẫn có thể bị nhầm. Đây là gợi ý từ ảnh, không thay thế kiểm tra thực tế.",
        "analysis_mode": "basic",
        "model_family": "MobileNetV3-Large-7",
        "class_count": len(CLASSES),
        "heatmap_url": heatmap_url,
        "filename": image_name,
        "ipm_advice": None if uncertain else get_ipm_advice(predicted_class, severity),
        "plan": plan_status(db, current_user),
    }


@router.get("/history")
def get_prediction_history(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return (
        db.query(Diagnosis)
        .filter(Diagnosis.owner_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .all()
    )
