# BỘ QUY TẮC VÀ NGỮ CẢNH DỰ ÁN (PROJECT CONTEXT & RULES)

Tài liệu này đóng vai trò cung cấp ngữ cảnh toàn diện cho bất kỳ hệ thống AI (Claude, Cursor, Copilot) hoặc lập trình viên nào thao tác trên dự án này. BẮT BUỘC tuân thủ các quy tắc dưới đây.

## 1. Tổng quan Project
- **Ứng dụng:** Mobile App (Flutter) chẩn đoán bệnh trên lá lúa.
- **Backend API:** FastAPI (Xử lý ảnh & suy luận AI).
- **Thuật toán cốt lõi (Đề tài NCKH):** Hệ thống Hybrid-CAM (Kết hợp Grad-CAM++ và HSV Vegetation mask) giúp tăng độ chính xác tuyệt đối bằng cách triệt tiêu nhiễu từ ảnh môi trường.

## 2. Công thức Toán học Tối thượng
Khi xử lý ảnh và hiển thị kết quả, phải bám sát công thức:
**$H_{Hybrid} = H_{AI} \odot M_{veg}$**
- $H_{AI}$: Grad-CAM++ Heatmap (Từ MobileNetV2).
- $M_{veg}$: Vegetation Mask (Mặt nạ diệp lục tạo từ không gian màu HSV).
- $\odot$: Phép nhân ma trận Hadamard (Element-wise).
- **% Độ nặng (Severity):** $(N_{disease} / N_{leaf}) \times 100$. (Luôn phải check `N_leaf > 0` để chặn lỗi chia cho 0).

$\rightarrow$ **Giao diện App (Result Screen):** Bắt buộc chia làm 4 Tabs để giải thích trực quan: Ảnh gốc, $H_{AI}$, $M_{veg}$, và $H_{Hybrid}$ kèm % Severity.

## 3. Quy chuẩn Code (Coding Conventions)
- **Tên file:** Chuẩn `snake_case.dart` (VD: `scanner_viewmodel.dart`).
- **Tên class:** Chuẩn `PascalCase` (VD: `ScannerViewModel`).
- **Chất lượng code:** Bắt buộc tuân thủ Null-Safety tuyệt đối, sử dụng bộ quy tắc `flutter lint` chuẩn của Google.
- **Hardcode:** TUYỆT ĐỐI KHÔNG hardcode IP Backend trong code. Mọi cấu hình môi trường phải đặt trong `core/env/`.

## 4. Kiến trúc Mobile App (Flutter)
- **Design Pattern:** MVVM (Model - View - ViewModel).
- **State Management:** Dùng `Provider` (Ưu tiên sự gọn nhẹ, chuẩn mực và dễ maintain).
- **Luồng Tiền xử lý (Client-side):** Mọi ảnh chụp phải đi qua `image_processing_service.dart` để Resize (1024px) và Check Blur (chống ảnh mờ) trước khi gửi đi.
- **Xử lý Lỗi (Error Handling):** Các lỗi mạng, lỗi máy chủ, lỗi Parse JSON phải được đưa về `app_exceptions.dart` để xử lý tập trung. KHÔNG dùng `try-catch` chung chung báo lỗi vô nghĩa cho nông dân.

## 5. Kiến trúc Máy chủ (FastAPI)
- **Endpoint:** `/predict` (Nhận file ảnh qua multipart form-data).
- **Backend gánh tạ (Thick Server):** Toàn bộ xử lý nặng (CLAHE, tạo Mask HSV, chạy MobileNetV2) BẮT BUỘC đặt ở Backend. Không đẩy việc nặng về App.
- **Backward Compatibility:** Việc nâng cấp code Backend API cấm tuyệt đối làm ảnh hưởng (Crash) đến hệ thống React Web hiện tại.
- **Dữ liệu mầm bệnh:** Lớp "Bọ cánh cứng" bắt buộc dùng code name là `beetle` (Nghiêm cấm dùng từ `hispa`).
