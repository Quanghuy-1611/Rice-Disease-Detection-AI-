# 🌾 Rice Leaf Disease Detection AI

![Rice AI Banner](https://img.shields.io/badge/AI-MobileNetV2-blue) ![Explainable AI](https://img.shields.io/badge/Explainable_AI-Grad--CAM-orange) ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green) ![Edge Device](https://img.shields.io/badge/Mobile-TFLite-red)

> **Nhận diện bệnh lúa bằng Trí tuệ Nhân tạo (AI) với khả năng Giải thích mô hình (XAI).**

Dự án này là một hệ thống AI toàn diện giúp nhận diện và chẩn đoán **17 loại bệnh** và sâu hại phổ biến trên cây lúa. Hệ thống không chỉ cung cấp dự đoán với độ chính xác cao mà còn tích hợp công nghệ **Grad-CAM (Gradient-weighted Class Activation Mapping)** để "giải thích" lý do AI đưa ra quyết định bằng cách khoanh vùng (bôi đỏ) chính xác vị trí vết bệnh trên lá.

---

## 🌟 Tính năng nổi bật

- ⚡ **Siêu nhẹ & Tốc độ cao:** Mô hình cốt lõi (MobileNetV2) được tinh chỉnh và lượng hóa (quantization) xuống chuẩn `.tflite` với dung lượng chỉ **2.8MB**, sẵn sàng chạy offline trên các thiết bị di động (Edge Devices) mà không cần kết nối internet.
- 🔍 **Giải thích mô hình (Explainable AI):** Trực quan hóa bản đồ nhiệt (Heatmap) giúp kỹ sư nông nghiệp và nông dân hiểu rõ tại sao AI lại chẩn đoán ra loại bệnh đó.
- 🎯 **Độ chính xác cao:** Độ chính xác trung bình (Accuracy) đạt **> 84%** trên tập dữ liệu kiểm thử thực tế khó (850 ảnh).
- 🌐 **Hệ sinh thái đa nền tảng:**
  - **Backend:** Cung cấp API suy luận siêu tốc bằng FastAPI.
  - **Mobile App / Web:** Giao diện trực quan để quét ảnh bệnh lúa ngoài đồng ruộng.

---

## 📊 Đánh giá định lượng (Quantitative Results)
*Kết quả đánh giá trên tập dữ liệu chưa từng thấy (Unseen Data) với 850 ảnh thực tế (17 lớp bệnh x 50 ảnh/lớp).*

| Chỉ số | Kết quả thực tế | Ý nghĩa |
|---|:---:|---|
| **Accuracy (Độ chính xác)** | **84.0%** | Tỉ lệ dự đoán đúng lớp bệnh cao và ổn định, bao phủ được phần lớn các loại sâu bệnh. |
| **Confidence (Độ tự tin)** | **82.1%** | AI đưa ra quyết định một cách dứt khoát, không đoán mò. |
| **Activation Area (Độ khoanh vùng)** | **22.2%** | Grad-CAM tập trung chính xác vào ~20% diện tích ảnh (khu vực chứa vết bệnh thực sự), ít bị nhiễu. |

> **Điểm sáng:** Các loại sâu hại như *Rầy nâu (brown_planthopper)*, *Ốc bươu vàng (golden_apple_snail)*, *Sâu cuốn lá (leaf_roller)* đạt độ chính xác lên đến **96% - 100%**.

---

## 🛠️ Kiến trúc hệ thống (Tech Stack)

- **Mô hình AI:** TensorFlow 2 / Keras, MobileNetV2 (Transfer Learning), TFLite.
- **Explainable AI:** Grad-CAM.
- **Backend API:** FastAPI (Python), Uvicorn.
- **Xử lý ảnh:** OpenCV, Pillow, Numpy.
- **Dữ liệu:** SQLite.

---

## 🚀 Hướng dẫn cài đặt & Chạy (Local Setup)

### 1. Yêu cầu hệ thống
- Python 3.9+
- Git

### 2. Cài đặt

Clone dự án về máy:
```bash
git clone https://github.com/Quanghuy-1611/Rice-Disease-Detection-AI.git
cd Rice-Disease-Detection-AI
```

Tạo môi trường ảo và cài đặt thư viện:
```bash
python -m venv .venv
# Kích hoạt môi trường (Windows)
.venv\Scripts\activate
# Cài đặt thư viện
pip install -r backend/requirements.txt
```

### 3. Chạy Backend (FastAPI)
```bash
cd backend
uvicorn app.main:app --reload
```
API sẽ chạy tại địa chỉ: `http://localhost:8000`

---

## 📁 Cấu trúc thư mục chính

```text
├── backend/            # Backend API (FastAPI) + SQLite DB + model.keras
├── research/           # Notebooks, Scripts huấn luyện model và phân tích
├── tools/              # Các công cụ script hỗ trợ xử lý dataset
├── .gitignore          # Bỏ qua các file model lớn và dataset
└── README.md
```

---
*Dự án này được phát triển bởi [Quanghuy-1611](https://github.com/Quanghuy-1611).*
