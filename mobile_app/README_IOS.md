# RiceAI trên iPhone

Ứng dụng iOS dùng bundle ID `com.quanghuy1611.riceai`. Firebase iOS đã được đăng ký trong dự án `riceai-production`; cấu hình nằm trong `ios/Runner/GoogleService-Info.plist` và `lib/firebase_options.dart`.

## Build và cài trên iPhone

Cần một máy Mac có Xcode, Flutter và tài khoản Apple để ký ứng dụng. Trên Mac:

1. Mở dự án `mobile_app`, chạy `flutter pub get` và `flutter doctor -v` để kiểm tra công cụ.
2. Mở `ios/Runner.xcodeproj` bằng Xcode, chọn target **Runner**, vào **Signing & Capabilities** và chọn Apple Team. Giữ bundle ID `com.quanghuy1611.riceai`.
3. Kết nối iPhone, tin cậy máy Mac, bật Developer Mode trên iPhone nếu được yêu cầu.
4. Chạy backend trên địa chỉ có thể truy cập từ iPhone, ví dụ máy tính và iPhone cùng Wi-Fi. Sau đó chạy `flutter run --dart-define=API_BASE_URL=http://<IP-cua-may-chay-backend>:8015`.

`127.0.0.1` trên iPhone là chính iPhone, không phải laptop. Từ bản 1.1.0+4, người dùng có thể đổi địa chỉ tại **Hồ sơ → Máy chủ**: chế độ **Gần laptop** nhận URL HTTP cùng mạng, còn **Internet** nhận URL HTTPS của máy chủ từ xa. Hai địa chỉ được lưu riêng và được kiểm tra trước khi chuyển. Hướng dẫn chi tiết: [Kết nối iPhone hai chế độ](../docs/KET_NOI_IPHONE_HAI_CHE_DO.md). Đăng nhập email cần tài khoản đã xác minh email. Google Sign-In cần URL scheme có trong `ios/Runner/Info.plist`.

Trên Windows không thể chạy Xcode hay build Flutter iOS native trực tiếp. Workflow GitHub Actions tạo IPA chưa ký để cài qua AltServer hoặc công cụ sideload đang dùng trên máy.

## Không có Mac: GitHub Actions + Sideloadly

Workflow `.github/workflows/ios-unsigned.yml` chạy trên máy macOS của GitHub để tạo IPA **chưa ký**. Đây là app native Flutter, không phải web.

1. Đưa các thay đổi của dự án lên GitHub. Trong **Actions → Build iOS IPA for sideloading → Run workflow**, nhập `api_base_url` là URL backend mà iPhone truy cập được. Ví dụ khi cùng Wi-Fi: `http://192.168.1.10:8000`. Backend cần lắng nghe trên IP mạng LAN và tường lửa phải cho phép cổng tương ứng.
2. Khi workflow chạy xong, tải artifact `RiceAI-unsigned-IPA` và giải nén để lấy `RiceAI-unsigned.ipa`.
3. Trên Windows, cài Sideloadly từ [trang chính thức](https://sideloadly.io/). Kết nối iPhone bằng cáp, mở Sideloadly, chọn IPA vừa tải, nhập Apple ID của chính bạn và bấm Start. Hoàn tất các bước xác thực và tin cậy ứng dụng theo hướng dẫn trên iPhone.

Với Apple ID miễn phí, ứng dụng cài kiểu này có hiệu lực 7 ngày rồi cần ký lại; Sideloadly có chức năng làm mới. Không đưa mật khẩu Apple ID hoặc mã xác thực cho người khác hay vào GitHub Actions. Nếu muốn phân phối ổn định qua TestFlight/App Store, cần Apple Developer Program và quy trình ký/phát hành riêng.
