# RiceAI Web

Web React/Vite để phân loại ảnh cây lúa theo 7 lớp bằng API FastAPI. Backend mặc định ở `http://127.0.0.1:8015`; proxy được cấu hình trong `vite.config.js`.

## Chạy tại máy

Khởi động backend theo `backend/README_7_CLASS.md`, sau đó trong thư mục `frontend` chạy:

```powershell
npm ci
npm run dev -- --host 127.0.0.1 --port 5174
```

Nếu cổng 5174 đang được dùng, chọn cổng khác. Nếu backend dùng địa chỉ khác, đặt `VITE_API_TARGET` trước khi chạy Vite.

## Đăng nhập bằng email

Web dùng Firebase Authentication cùng dự án với ứng dụng di động. Người dùng đăng ký bằng địa chỉ email có thể nhận thư, mở liên kết xác minh trong hộp thư, rồi đăng nhập. Sau khi xác minh, web đổi Firebase ID token lấy phiên API tại `/api/auth/firebase/exchange`. Có thể gửi lại thư xác minh hoặc yêu cầu đặt lại mật khẩu tại trang đăng nhập.

Firebase Console của dự án cần bật phương thức Email/Password và cho phép miền chạy web trong Authorized domains. Backend cần tệp Firebase Admin credentials theo hướng dẫn của backend. Không đặt mật khẩu hoặc Admin credentials vào mã frontend.

## Kiểm tra

```powershell
npm run lint
npm run build
```
