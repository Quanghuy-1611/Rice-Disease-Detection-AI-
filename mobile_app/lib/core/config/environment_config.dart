/// Cấu hình kết nối theo từng môi trường.
///
/// Không ghi IP LAN cố định trong mã nguồn. Khi chạy trên điện thoại, truyền
/// địa chỉ FastAPI bằng `--dart-define=API_BASE_URL=http://192.168.x.x:8000`.
class EnvironmentConfig {
  const EnvironmentConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  static bool get isApiConfigured => apiBaseUrl.trim().isNotEmpty;

  static String get displayBaseUrl =>
      isApiConfigured ? apiBaseUrl : 'Chưa cấu hình máy chủ';
}
