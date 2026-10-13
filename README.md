# RiceAI — nhận diện bệnh cây lúa

Dự án gồm API FastAPI, giao diện web React, ứng dụng Flutter và bộ công cụ nghiên cứu mô hình. Các tập dữ liệu, checkpoint và kết quả thí nghiệm nằm trong `research/` và `model_benchmark/`; không nên xóa khi chưa đối chiếu chiến dịch huấn luyện tương ứng.

## Cấu trúc

| Thư mục | Nội dung |
| --- | --- |
| `backend/` | API, dữ liệu ứng dụng và mô hình triển khai |
| `frontend/` | Giao diện web React/Vite |
| `mobile_app/` | Ứng dụng Flutter |
| `model_benchmark/` | Mã huấn luyện, cấu hình, kết quả đánh giá |
| `research/` | Dữ liệu, split, khóa thí nghiệm và ghi chép nghiên cứu |
| `docs/reports/` | Tài liệu Word và báo cáo dự án |
| `docs/archives/` | Gói lưu trữ kết quả |
| `scripts/reports/` | Script tạo và chỉnh sửa báo cáo |
| `scripts/runs/` | Lệnh train và đánh giá mô hình |
| `scripts/maintenance/` | Script bảo trì |
| `tools/` | Công cụ dữ liệu và báo cáo phụ trợ |

## Chạy ứng dụng

Yêu cầu Python và Node.js. Từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm ci
```

Chạy `start_backend.bat` và `start_frontend.bat` trong hai cửa sổ riêng. API dùng cổng 8015 và lắng nghe trên cả localhost lẫn mạng LAN để ứng dụng iPhone có thể chẩn đoán qua Wi-Fi; web dùng cổng 5173. `START_RICEAI.bat` khởi động cả hai. Khi dùng máy chủ trên laptop, iPhone và laptop cần cùng mạng và laptop phải bật. Ứng dụng iOS cũ dùng IP đặt lúc build; bản 1.1.0+4 cho phép đổi IP trong ứng dụng. Đăng nhập bằng email đã xác minh qua Firebase; vai trò Admin/Employee được quản lý trong cơ sở dữ liệu backend.

Để bật bản chạy thử trên laptop, dùng `BAT_RICEAI.cmd` và đợi thông báo API/web sẵn sàng. Bản iOS 1.1.0+4 cho phép lưu địa chỉ laptop và địa chỉ máy chủ Internet riêng trong **Hồ sơ → Máy chủ**. Xem [cách kết nối iPhone ở nhà và khi đi xa](docs/KET_NOI_IPHONE_HAI_CHE_DO.md). Máy chủ Internet cần VPS riêng; repository đã có gói Docker Compose nhưng chưa có VPS nào được triển khai.

Basic nhận một ảnh/lượt và có 15 lượt/tháng. Plus nhận 1–5 ảnh/lượt và có 80 lượt/tháng; Admin/Employee không bị giới hạn. Plus dùng hai mô hình phân loại cùng một nhãn và DeepLabV3+ hỗ trợ lọc bản đồ nhiệt cho bệnh lá. Cả hai chế độ có thể trả lời **chưa đủ chắc chắn**. Plus chỉ bật khi ba checkpoint khớp manifest kiểm định `backend/app/model/plus_release.json`; sau khi train lại phải kiểm định, tạo manifest mới và khởi động lại backend. Xem [kiểm định Plus và kế hoạch bổ sung ảnh](docs/PLUS_VALIDATION_AND_NEXT_IMAGES.md).

Trang gói sử dụng cho phép gửi yêu cầu Plus; hệ thống hiện **chưa tích hợp cổng thanh toán**. Admin có thể kích hoạt thủ công sau khi xác minh thanh toán bên ngoài, hoặc cấp quyền thử nghiệm. Việc gửi yêu cầu không tự trừ tiền.

Gợi ý xử lý từ ảnh chỉ là bước kiểm tra ban đầu, không tự xác định ngưỡng cần phun thuốc. Xem [phạm vi hướng dẫn IPM](docs/IPM_GUIDANCE.md).

Các script nghiên cứu được gọi từ thư mục gốc, ví dụ:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\runs\RUN_RESEARCH_7_CLASSES.ps1
```

Các script này có thể cần `model_benchmark/.venv312`, CUDA và dữ liệu nghiên cứu tại máy. Xem [hướng dẫn benchmark](model_benchmark/README.md) và [hướng dẫn backend 7 lớp](backend/README_7_CLASS.md) trước khi chạy.

## Ghi chú về dữ liệu

`.venv/`, cache, file cài đặt và output tạm không thuộc mã nguồn. Mô hình, dữ liệu nghiên cứu và kết quả đánh giá có giá trị tái lập; cần xem xét riêng trước khi dọn dung lượng.
