"""
evaluate_gradcam.py
- Load AI model thực tế đang chạy trên web
- Lấy ngẫu nhiên 10 ảnh/lớp (18 lớp, bỏ southern_black_streaked_dwarf)
- Chạy Grad-CAM cũ trên 180 ảnh
- Lưu ảnh kết quả vào research/evaluation/gradcam_v1/
- Tính Accuracy, Confidence trung bình và Activation Area Ratio cho từng lớp
- Xuất báo cáo evaluation_report.json và evaluation_report.txt
"""

import os
import sys
import json
import random
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from PIL import Image
import io

random.seed(42)  # Đảm bảo kết quả reproducible (không random mỗi lần chạy)

# ===== CẤU HÌNH =====
DATASET_DIR    = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
MODEL_PATH     = r"D:\Phát hiện bệnh cây lúa\backend\app\model\best_stage2.keras"
CLASS_MAP_PATH = r"D:\Phát hiện bệnh cây lúa\backend\app\model\class_indices.json"
OUTPUT_DIR     = r"D:\Phát hiện bệnh cây lúa\research\evaluation\gradcam_v1"
SAMPLES_PER_CLASS = 50
SKIP_CLASSES = {"southern_black_streaked_dwarf"}

# ===== LOAD MODEL =====
print("Loading model...")
keras_model = load_model(MODEL_PATH)
with open(CLASS_MAP_PATH, "r", encoding="utf-8") as f:
    idx_to_class = {int(k): v for k, v in json.load(f).items()}
class_to_idx = {v: k for k, v in idx_to_class.items()}
print(f"Model loaded. Tổng số lớp: {len(idx_to_class)}\n")

# ===== HÀM GRAD-CAM (dùng đúng logic như trong cv_utils.py trên web) =====
def run_gradcam(image_bytes, model, class_index):
    """
    Trả về (superimposed_img, activation_ratio)
    activation_ratio = % pixel trên heatmap có giá trị > 0.5 * max
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    resized = cv2.resize(img_rgb, (224, 224))
    img_array = preprocess_input(np.expand_dims(resized, 0).astype(np.float32))

    # Tìm layer conv cuối (đúng cách của cv_utils.py)
    last_conv_layer_name = None
    for layer in reversed(model.layers):
        try:
            if hasattr(layer, 'output') and hasattr(layer.output, 'shape') and len(layer.output.shape) == 4:
                last_conv_layer_name = layer.name
                break
        except:
            continue

    grad_model = Model(
        inputs=[model.inputs],
        outputs=[model.get_layer(last_conv_layer_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_out = conv_outputs[0]
    heatmap = conv_out @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-8)
    heatmap = heatmap.numpy()

    # Activation Area Ratio: % pixel > 50% của max
    activation_ratio = float(np.mean(heatmap > 0.5))

    # Overlay lên ảnh gốc
    h_up = cv2.resize(heatmap, (img_bgr.shape[1], img_bgr.shape[0]))
    h_color = cv2.applyColorMap(np.uint8(255 * h_up), cv2.COLORMAP_JET)
    superimposed = cv2.addWeighted(img_bgr, 0.6, h_color, 0.4, 0)

    return superimposed, activation_ratio

# ===== VÒNG LẶP ĐÁNH GIÁ =====
os.makedirs(OUTPUT_DIR, exist_ok=True)

all_classes = sorted([
    d for d in os.listdir(DATASET_DIR)
    if os.path.isdir(os.path.join(DATASET_DIR, d)) and d not in SKIP_CLASSES
])

total_images = len(all_classes) * SAMPLES_PER_CLASS
print(f"Bắt đầu đánh giá: {len(all_classes)} lớp × {SAMPLES_PER_CLASS} ảnh = {total_images} ảnh\n")

results = {}
img_counter = 0

for class_name in all_classes:
    class_dir = os.path.join(DATASET_DIR, class_name)
    class_idx = class_to_idx.get(class_name)
    if class_idx is None:
        print(f"[SKIP] {class_name} - không có trong class_indices.json")
        continue

    all_imgs = [f for f in os.listdir(class_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    sample = random.sample(all_imgs, min(SAMPLES_PER_CLASS, len(all_imgs)))

    out_dir = os.path.join(OUTPUT_DIR, class_name)
    os.makedirs(out_dir, exist_ok=True)

    confidences, activation_ratios = [], []
    correct = 0

    print(f"[{class_name}] ({len(sample)} ảnh)")

    for fname in sample:
        fpath = os.path.join(class_dir, fname)
        with open(fpath, "rb") as f:
            image_bytes = f.read()

        # Bước 1: Dự đoán
        img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
        arr = preprocess_input(np.expand_dims(np.array(img_pil), 0).astype(np.float32))
        preds = keras_model.predict(arr, verbose=0)[0]
        pred_idx = int(np.argmax(preds))
        confidence = float(preds[pred_idx])
        pred_class = idx_to_class.get(pred_idx, "unknown")

        if pred_class == class_name:
            correct += 1
        confidences.append(confidence)

        # Bước 2: Grad-CAM với đúng class_idx của lớp này
        try:
            superimposed, act_ratio = run_gradcam(image_bytes, keras_model, class_idx)
            activation_ratios.append(act_ratio)
            # Tên file: gradcam_[đúng/sai]_[confidence]_[tên gốc]
            tag = "OK" if pred_class == class_name else f"WRONG_{pred_class}"
            out_fname = f"gradcam_{tag}_{int(confidence*100)}pct_{fname}"
            cv2.imwrite(os.path.join(out_dir, out_fname), superimposed)
        except Exception as e:
            print(f"  Lỗi GradCAM {fname}: {e}")

        img_counter += 1
        sys.stdout.write(f"\r  Tiến độ: {img_counter}/{total_images}")
        sys.stdout.flush()

    print()  # newline sau progress

    valid_ar = [x for x in activation_ratios if x is not None]
    results[class_name] = {
        "samples": len(sample),
        "correct": correct,
        "accuracy_pct": round(correct / len(sample) * 100, 1),
        "mean_confidence_pct": round(float(np.mean(confidences)) * 100, 1),
        "mean_activation_area_pct": round(float(np.mean(valid_ar)) * 100, 1) if valid_ar else None,
    }
    r = results[class_name]
    print(f"  -> Accuracy: {r['accuracy_pct']}% | Confidence: {r['mean_confidence_pct']}% | ActivArea: {r['mean_activation_area_pct']}%\n")

# ===== XUẤT BÁO CÁO =====
report_json = os.path.join(OUTPUT_DIR, "evaluation_report.json")
with open(report_json, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

report_txt = os.path.join(OUTPUT_DIR, "evaluation_report.txt")
accs, confs, areas = [], [], []
with open(report_txt, "w", encoding="utf-8") as f:
    f.write("=" * 72 + "\n")
    f.write("  BÁO CÁO ĐÁNH GIÁ GRAD-CAM V1 (BASELINE)  \n")
    f.write("  Script: evaluate_gradcam.py | Seed: 42     \n")
    f.write("=" * 72 + "\n\n")
    f.write(f"{'Lớp bệnh':<38} {'Acc%':>5} {'Conf TB%':>9} {'ActivArea%':>11}\n")
    f.write("-" * 72 + "\n")
    for cls, r in results.items():
        f.write(f"{cls:<38} {r['accuracy_pct']:>5} {r['mean_confidence_pct']:>9} {str(r['mean_activation_area_pct']):>11}\n")
        accs.append(r['accuracy_pct'])
        confs.append(r['mean_confidence_pct'])
        if r['mean_activation_area_pct'] is not None:
            areas.append(r['mean_activation_area_pct'])
    f.write("=" * 72 + "\n")
    f.write(f"{'TRUNG BÌNH TỔNG THỂ':<38} {round(np.mean(accs),1):>5} {round(np.mean(confs),1):>9} {round(np.mean(areas),1):>11}\n")
    f.write("\n\nGHI CHÚ:\n")
    f.write("  Accuracy    : % ảnh AI dự đoán đúng đúng lớp bệnh\n")
    f.write("  Confidence  : % độ tự tin trung bình của AI\n")
    f.write("  ActivArea   : % diện tích ảnh bị 'bôi đỏ' trên Heatmap\n")
    f.write("               Thấp (10-25%) = tập trung chính xác vào vết bệnh\n")
    f.write("               Cao  (>40%)   = bị nhiễu, loang khắp ảnh\n")

print("\n" + "=" * 72)
print("HOÀN THÀNH!")
print(f"Ảnh kết quả : {OUTPUT_DIR}")
print(f"Báo cáo TXT : {report_txt}")
print(f"Báo cáo JSON: {report_json}")
print("=" * 72)
