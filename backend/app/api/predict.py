from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import io
import os
import json
import uuid
import numpy as np
from PIL import Image
from app.database import get_db
from app.models import Diagnosis
from app.api.auth import get_current_user
from app.api.cv_utils import generate_gradcam_heatmap
from app.api.ipm_advisor import get_ipm_advice

import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

router = APIRouter()

# 1. Khởi tạo Model và Labels khi Backend khởi động
MODEL_PATH = "app/model/best_stage2.keras"
CLASS_MAP_PATH = "app/model/class_indices.json"

keras_model = None
idx_to_class = {}

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(CLASS_MAP_PATH):
        print("Loading AI Model (Keras) and Labels...")
        keras_model = load_model(MODEL_PATH)
        
        with open(CLASS_MAP_PATH, "r", encoding="utf-8") as f:
            idx_to_class = json.load(f)
            # Convert keys from string to int
            idx_to_class = {int(k): v for k, v in idx_to_class.items()}
        print("Model loaded successfully!")
    else:
        print("WARNING: Model or class_indices.json not found!")
except Exception as e:
    import traceback
    print("Error loading model:", e)
    traceback.print_exc()


@router.post("/predict")
async def predict_image(
    file: UploadFile = File(...), 
    severity: str = Form("low"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Nhận ảnh từ client, dùng AI (MobileNetV2) dự đoán bệnh,
    sinh bản đồ nhiệt (Grad-CAM) và lưu lịch sử.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Vui lòng tải lên một tệp hình ảnh.")

    if keras_model is None:
        raise HTTPException(status_code=500, detail="Hệ thống AI chưa được khởi tạo. Vui lòng kiểm tra lại file model.")

    try:
        contents = await file.read()
        
        # Lưu file gốc
        os.makedirs("uploads", exist_ok=True)
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join("uploads", unique_filename)
        with open(filepath, "wb") as f:
            f.write(contents)

        # 1. Tiền xử lý ảnh cho Keras Model
        img = Image.open(io.BytesIO(contents)).convert('RGB')
        img_resized = img.resize((224, 224))
        img_array = np.array(img_resized)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array.astype(np.float32))

        # 2. Dự đoán bệnh
        preds = keras_model.predict(img_array)[0]
        predicted_idx = int(np.argmax(preds))
        confidence = float(preds[predicted_idx])
        predicted_class = idx_to_class.get(predicted_idx, "unknown")

        # 3. Chạy Grad-CAM (Chỉ khi có bệnh)
        heatmap_url = None
        if predicted_class != "normal":
            # Tạo bản đồ nhiệt
            heatmap_filename = generate_gradcam_heatmap(contents, keras_model, predicted_idx, output_dir="uploads")
            if heatmap_filename:
                heatmap_url = f"/uploads/{heatmap_filename}"

        # 4. Lưu vào Database
        diagnosis = Diagnosis(
            image_filename=unique_filename,
            prediction=predicted_class,
            confidence=confidence,
            owner_id=current_user.id
        )
        db.add(diagnosis)
        db.commit()

        # 5. Gọi hệ chuyên gia tư vấn IPM
        ipm_advice = get_ipm_advice(predicted_class, severity)

        return {
            "success": True,
            "prediction": predicted_class,
            "confidence": confidence,
            "heatmap_url": heatmap_url,
            "filename": unique_filename,
            "ipm_advice": ipm_advice
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_prediction_history(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Lấy danh sách lịch sử quét bệnh của người dùng hiện tại
    """
    history = db.query(Diagnosis).filter(Diagnosis.owner_id == current_user.id).order_by(Diagnosis.created_at.desc()).all()
    return history
