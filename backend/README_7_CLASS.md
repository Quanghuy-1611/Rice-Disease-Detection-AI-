# RiceAI: triển khai 7 lớp

Backend dùng checkpoint MobileNetV3 Large `app/model/mobilenetv3large_7class_seed42.pt` từ chiến dịch huấn luyện 7 lớp. Thứ tự nhãn được kiểm tra ngay khi nạp mô hình:

1. `bacterial_leaf_blight`
2. `brown_spot`
3. `golden_apple_snail`
4. `leaf_roller`
5. `normal`
6. `tungro`
7. `weeds`

Chạy backend từ thư mục `backend` bằng Python 3.11 hoặc 3.12 sau khi cài `requirements.txt` và cấu hình `SECRET_KEY` trong `.env`. API mặc định chạy trên cổng 8015 theo `start_backend.bat`. Web Vite chuyển tiếp `/api` và `/uploads` đến cổng này. Với Flutter, truyền `--dart-define=API_BASE_URL=http://<địa-chỉ-máy-chủ>:8015` khi chạy trên thiết bị.

`GET /api/health` trả về `model_ready`, `model_classes` và trạng thái cẩm nang. `POST /api/predict` nhận `analysis_mode=basic`, trả về nhãn, độ tin cậy và ảnh Grad-CAM cho lớp khác `normal`. Phần Agri-CAM/Plus cũ chưa tương thích checkpoint PyTorch này và không được hiển thị trong luồng chẩn đoán mới. `severity` là mức độ người dùng tự nhập để tham khảo trong tư vấn IPM; mô hình không ước lượng mức độ bệnh.

Lịch sử cũ vẫn được giữ nguyên trong cơ sở dữ liệu và có thể chứa nhãn của mô hình 19 lớp trước đây. Chỉ dự đoán mới và cẩm nang hiện tại bị giới hạn ở 7 lớp.

## Theo dõi tải trên laptop

Trang Quản trị hiển thị số tài khoản và thiết bị đang hoạt động trong 2 phút gần nhất, chia theo web/iPhone/Android. Web và app gửi nhịp báo trạng thái 45 giây một lần khi đang mở; cùng một tài khoản trên nhiều thiết bị chỉ tính là một người dùng. Bản iPhone đã cài trước tính năng này cần được build và cài lại mới xuất hiện trong số liệu trực tiếp.

Trang này cũng hiển thị số ảnh đang phân tích và số yêu cầu đang chờ. Grad-CAM dùng chung một mô hình nên các yêu cầu được xử lý lần lượt. Mặc định nhận tối đa 20 yêu cầu chẩn đoán đồng thời (`RICEAI_MAX_IN_FLIGHT`); khi đầy, API trả `503` cùng `Retry-After: 5` để ứng dụng mời người dùng thử lại. `RICEAI_TORCH_THREADS` mặc định là 2 trên máy phát triển hiện tại và có thể điều chỉnh theo máy chủ khác.

Các số liệu này phản ánh một tiến trình API trên laptop, không phải chứng nhận chịu tải 1.000 người. Cần kiểm thử tải đầy đủ qua web/app và hạ tầng máy chủ phù hợp trước khi công bố giới hạn người dùng thực tế.

Đo lại bằng `python -m tests.benchmark_basic_local` từ thư mục `backend`. Bài đo dùng ảnh tạo trong bộ nhớ, đi qua toàn bộ tuyến `/api/predict` và cơ sở dữ liệu tạm nhưng bỏ qua mạng LAN và dịch vụ đăng nhập bên ngoài. Trên laptop i7-13700HX/16 GB hiện tại, 20 yêu cầu đồng thời hoàn tất trong khoảng 1,7 giây; với 25 yêu cầu cùng lúc, 20 hoàn tất và 5 nhận `503`. Đây là mức kiểm tra phù hợp cho bản trình diễn, chưa phải cam kết cho mọi ảnh và mọi điều kiện mạng.
