# Kết nối RiceAI trên iPhone ở nhà và khi đi xa

## 1. Cùng mạng với laptop

1. Bật laptop và chạy `BAT_RICEAI.cmd`. Đợi dòng `RiceAI is running`.
2. Cho iPhone và laptop vào cùng một mạng có cho phép hai thiết bị liên lạc.
3. Trong cửa sổ CMD, lấy dòng `iPhone API`, ví dụ `http://192.168.100.155:8015/docs`.
4. Thử đường dẫn đó trong Safari trên iPhone. Nếu Safari không mở được, app cũng chưa thể chẩn đoán.
5. Trong RiceAI → **Hồ sơ → Máy chủ → Gần laptop**, nhập địa chỉ trên nhưng bỏ `/docs`, rồi chọn **Kiểm tra & lưu**.

IP của laptop có thể đổi khi chuyển Wi-Fi. Chỉ cần cập nhật địa chỉ ở mục **Máy chủ**, không cần build lại ứng dụng sau khi đã cài bản hỗ trợ chọn máy chủ.

## 2. Đi xa khi laptop vẫn bật

Đây là cách thử chế độ Internet trước khi có VPS. Cài Tailscale trên laptop và iPhone, đăng nhập cùng tailnet. Trên laptop, bật `BAT_RICEAI.cmd`, rồi chạy `tailscale serve --bg 8015` và lấy URL HTTPS bằng `tailscale serve status`. Bật Tailscale trên iPhone, thử `<URL HTTPS>/api/health` trong Safari, rồi lưu URL đó ở **Hồ sơ → Máy chủ → Internet**. Laptop vẫn phải bật và nối Internet. Tailscale Serve chỉ cho thiết bị trong tailnet truy cập; không dùng Funnel để mở API công khai.

## 3. Qua Internet khi laptop tắt

Chế độ này cần một máy chủ khác luôn hoạt động. Gói `backend/Dockerfile` và `backend/compose.yaml` chuẩn bị API cho một VPS Linux chạy Docker Compose. Cấu hình hiện tại dành cho **thử nghiệm riêng tư**: API chỉ mở ở `127.0.0.1:8015` trên VPS và dùng Tailscale Serve để cấp địa chỉ HTTPS cho các thiết bị trong cùng tailnet. Không dùng Tailscale Funnel hoặc mở trực tiếp cổng 8015 ra Internet.

Trên VPS, sau khi cài Docker, Docker Compose, Git LFS và Tailscale:

1. Clone repository, chạy `git lfs pull` và xác nhận ba checkpoint Plus trong `backend/app/model/` là file mô hình thật, không phải LFS pointer.
2. Chép `backend/.env.example` thành `backend/.env`, đặt `SECRET_KEY` ngẫu nhiên. Chép khóa Firebase Admin riêng vào `backend/firebase-adminsdk.json`; không đưa khóa vào Git hoặc image Docker.
3. Nếu muốn giữ vai trò, hạn mức và lịch sử hiện tại, dừng API trên laptop rồi chép `backend/paddy_disease.db` vào `backend/runtime/paddy_disease.db` trên VPS; chép cả `backend/uploads/`. Đây là bản sao **một lần**: hai máy chủ không tự đồng bộ dữ liệu về sau.
4. Trong `backend/`, chạy `docker compose up -d --build`, sau đó thử `http://127.0.0.1:8015/api/health` trên VPS. Kiểm tra `model_ready` và `plus_model_ready` đều `true` trước khi dùng Plus.
5. Đăng nhập Tailscale trên VPS và iPhone bằng cùng tailnet. Trên VPS chạy `tailscale serve --bg 8015`, rồi dùng `tailscale serve status` để lấy URL HTTPS `*.ts.net`. Nếu Tailscale yêu cầu bật chứng chỉ HTTPS, hoàn tất bước đó trong tài khoản Tailscale.
6. Trên iPhone, bật Tailscale rồi mở `<URL HTTPS>/api/health` bằng Safari. Trong RiceAI → **Hồ sơ → Máy chủ → Internet**, nhập URL HTTPS không có `/api/health` và chọn **Kiểm tra & lưu**.

API trên VPS dùng SQLite và thư mục ảnh gắn vào `backend/runtime/` và `backend/uploads/`; sao lưu cả hai. Sau khi chép dữ liệu lên VPS, nên coi VPS là nguồn dữ liệu chính. Nếu tiếp tục chẩn đoán ở cả laptop và VPS, lịch sử và lượt dùng sẽ tách thành hai bản; cần triển khai đồng bộ dữ liệu trước khi dùng song song cho nhiều người.

**Trạng thái hiện tại:** Chưa có VPS và URL HTTPS thật, nên chưa thể kiểm thử chế độ Internet trên iPhone. App iOS đang cài cũng cần bản cập nhật có mục chọn hai máy chủ. Tài liệu này là quy trình triển khai khi có máy chủ, không phải xác nhận đã triển khai.
