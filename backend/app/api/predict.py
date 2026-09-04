"""Prediction API with a transparent Basic/Plus explainability contract.

Basic uses one raw Grad-CAM.  Plus uses the same classifier with Agri-CAM;
therefore Plus must never claim a higher classification F1 by itself.
"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import os
import uuid

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

from app.database import get_db
from app.models import Diagnosis
from app.api.auth import get_current_user
from app.api.ipm_advisor import get_ipm_advice
from app.api import agri_cam


router = APIRouter()
PROJECT_MODEL_DIR = "app/model"
MODEL_PATH = os.getenv("RICEAI_MODEL_PATH", f"{PROJECT_MODEL_DIR}/best_stage2.keras")
CLASS_MAP_PATH = os.getenv("RICEAI_CLASS_MAP_PATH", f"{PROJECT_MODEL_DIR}/class_indices.json")
MODEL_MANIFEST_PATH = os.getenv("RICEAI_MODEL_MANIFEST_PATH", "")
CALIBRATION_PATH = os.getenv(
    "AGRICAM_CALIBRATION_PATH", "app/data/agri_cam_calibration.json"
)

keras_model: tf.keras.Model | None = None
idx_to_class: dict[int, str] = {}
model_preprocessing = "mobilenet_v2"
model_family = "MobileNetV2"


def _load_manifest() -> dict:
    if not MODEL_MANIFEST_PATH or not os.path.isfile(MODEL_MANIFEST_PATH):
        return {}
    with open(MODEL_MANIFEST_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


try:
    if os.path.exists(MODEL_PATH) and os.path.exists(CLASS_MAP_PATH):
        manifest = _load_manifest()
        model_family = manifest.get("model", {}).get("family", "MobileNetV2")
        expected_range = manifest.get("preprocessing", {}).get("backend_expected_range")
        # The V3 bundle contains Rescaling in the model graph.  Applying the
        # V2 scaler here would double-transform the input and invalidate V3.
        model_preprocessing = (
            "raw_rgb_0_255" if expected_range == [0.0, 255.0] else "mobilenet_v2"
        )
        print(f"Loading AI model: {model_family} ({MODEL_PATH})")
        keras_model = load_model(MODEL_PATH, compile=False)
        with open(CLASS_MAP_PATH, "r", encoding="utf-8") as file:
            idx_to_class = {int(key): value for key, value in json.load(file).items()}
        print(f"Model loaded. preprocessing={model_preprocessing}")
    else:
        print("WARNING: model or class_indices.json not found; prediction API unavailable.")
except Exception as error:
    import traceback

    print("Error loading model:", error)
    traceback.print_exc()


def _predict(image_bgr: np.ndarray) -> tuple[np.ndarray, int, float, str]:
    if keras_model is None:
        raise RuntimeError("Hệ thống AI chưa được khởi tạo.")
    model_input = agri_cam.prepare_input(image_bgr, model_preprocessing)
    probabilities = keras_model(model_input, training=False).numpy()[0]
    predicted_index = int(np.argmax(probabilities))
    return (
        model_input,
        predicted_index,
        float(probabilities[predicted_index]),
        idx_to_class.get(predicted_index, "unknown"),
    )


def _url(filename: str | None) -> str | None:
    return f"/uploads/{filename}" if filename else None


def _basic_gradcam(
    image_bgr: np.ndarray, model_input: np.ndarray, predicted_index: int
) -> np.ndarray:
    assert keras_model is not None
    _, heatmap = agri_cam.compute_cam_maps(
        keras_model,
        model_input,
        predicted_index,
        layers=agri_cam.default_cam_layers(keras_model, use_multilayer=False),
        method="gradcam",
        image_size=(image_bgr.shape[1], image_bgr.shape[0]),
    )
    return heatmap


def _plus_agri_cam(
    image_bgr: np.ndarray,
    model_input: np.ndarray,
    predicted_index: int,
    predicted_class: str,
) -> tuple[str, dict]:
    """Execute Agri-CAM and return the compatible raw Grad-CAM URL plus payload."""

    assert keras_model is not None
    basic_heatmap = _basic_gradcam(image_bgr, model_input, predicted_index)
    _, multi_heatmap = agri_cam.compute_cam_maps(
        keras_model,
        model_input,
        predicted_index,
        layers=agri_cam.default_cam_layers(keras_model, use_multilayer=True),
        method="gradcam++",
        image_size=(image_bgr.shape[1], image_bgr.shape[0]),
    )
    leaf_mask, mask_info = agri_cam.create_disease_aware_leaf_mask(image_bgr, predicted_class)
    hybrid_heatmap = agri_cam.apply_leaf_constraint(multi_heatmap, leaf_mask)
    calibration = agri_cam.load_calibration(CALIBRATION_PATH)
    severity = agri_cam.estimate_severity(
        hybrid_heatmap, leaf_mask, predicted_class, calibration
    )

    # K=5 uncertainty passes only run when thresholds are genuinely calibrated.
    # Returning a fake percentage beforehand would not be scientifically valid.
    if severity.get("severity_percent") is not None:
        samples: list[float] = []
        for variant in agri_cam.make_stability_variants(image_bgr):
            variant_input = agri_cam.prepare_input(variant, model_preprocessing)
            _, variant_multi = agri_cam.compute_cam_maps(
                keras_model,
                variant_input,
                predicted_index,
                layers=agri_cam.default_cam_layers(keras_model, use_multilayer=True),
                method="gradcam++",
                image_size=(variant.shape[1], variant.shape[0]),
            )
            variant_mask, _ = agri_cam.create_disease_aware_leaf_mask(variant, predicted_class)
            variant_hybrid = agri_cam.apply_leaf_constraint(variant_multi, variant_mask)
            estimate = agri_cam.estimate_severity(
                variant_hybrid, variant_mask, predicted_class, calibration
            )
            if estimate.get("severity_percent") is not None:
                samples.append(float(estimate["severity_percent"]))
        severity = agri_cam.attach_reliability(
            severity, samples, str(mask_info["mask_status"]), calibration
        )

    images = agri_cam.save_agri_visualisations(
        image_bgr,
        basic_heatmap,
        multi_heatmap,
        leaf_mask,
        hybrid_heatmap,
        output_dir="uploads",
    )
    return _url(images["heatmap_url"]) or "", {
        "ai_heatmap_url": _url(images["ai_heatmap_url"]),
        "leaf_mask_url": _url(images["leaf_mask_url"]),
        "hybrid_heatmap_url": _url(images["hybrid_heatmap_url"]),
        "severity_percent": severity.get("severity_percent"),
        "severity_method": severity.get("severity_method"),
        "uncertainty_std_percent": severity.get("uncertainty_std_percent"),
        "stability_sample_count": severity.get("stability_sample_count", 0),
        "reliability": severity.get("reliability"),
        "mask": mask_info,
        "background_attention_leakage": round(
            agri_cam.background_attention_leakage(multi_heatmap, leaf_mask), 5
        ),
        "calibration_status": calibration.get("status", "not_calibrated"),
        "method": "agri_cam_v1_multilayer_gradcampp_class_aware_mask",
    }


@router.post("/predict")
async def predict_image(
    file: UploadFile = File(...),
    severity: str = Form("low"),
    analysis_mode: str = Form("basic"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Predict a rice image, preserving the old fields for legacy clients."""

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Vui lòng tải lên một tệp hình ảnh.")
    if analysis_mode not in {"basic", "plus"}:
        raise HTTPException(status_code=422, detail="analysis_mode chỉ nhận basic hoặc plus.")
    if keras_model is None:
        raise HTTPException(status_code=500, detail="Hệ thống AI chưa được khởi tạo.")

    try:
        contents = await file.read()
        image_bgr = agri_cam.decode_bgr(contents)
        model_input, predicted_index, confidence, predicted_class = _predict(image_bgr)

        os.makedirs("uploads", exist_ok=True)
        unique_filename = f"{uuid.uuid4()}_{os.path.basename(file.filename or 'image.jpg')}"
        with open(os.path.join("uploads", unique_filename), "wb") as output:
            output.write(contents)

        heatmap_url: str | None = None
        agri_cam_payload: dict | None = None
        if predicted_class != "normal":
            if analysis_mode == "plus":
                heatmap_url, agri_cam_payload = _plus_agri_cam(
                    image_bgr, model_input, predicted_index, predicted_class
                )
            else:
                basic_heatmap = _basic_gradcam(image_bgr, model_input, predicted_index)
                images = agri_cam.save_agri_visualisations(
                    image_bgr,
                    basic_heatmap,
                    basic_heatmap,
                    np.ones_like(basic_heatmap),
                    basic_heatmap,
                    output_dir="uploads",
                )
                heatmap_url = _url(images["heatmap_url"])

        diagnosis = Diagnosis(
            image_filename=unique_filename,
            prediction=predicted_class,
            confidence=confidence,
            owner_id=current_user.id,
        )
        db.add(diagnosis)
        db.commit()

        response = {
            "success": True,
            "prediction": predicted_class,
            "confidence": confidence,
            "analysis_mode": analysis_mode,
            "model_family": model_family,
            "heatmap_url": heatmap_url,
            "filename": unique_filename,
            "ipm_advice": get_ipm_advice(predicted_class, severity),
        }
        if agri_cam_payload is not None:
            response["agri_cam"] = agri_cam_payload
        return response
    except HTTPException:
        raise
    except Exception as error:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/history")
def get_prediction_history(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return (
        db.query(Diagnosis)
        .filter(Diagnosis.owner_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .all()
    )
