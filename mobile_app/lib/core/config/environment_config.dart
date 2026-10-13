import 'package:shared_preferences/shared_preferences.dart';

enum RiceAiServerMode { local, internet }

/// Keep separate addresses for the laptop and a future hosted API.
class EnvironmentConfig {
  const EnvironmentConfig._();

  static const String _buildBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );
  static const String _legacyKey = 'riceai_api_base_url';
  static const String _localKey = 'riceai_local_api_base_url';
  static const String _internetKey = 'riceai_internet_api_base_url';
  static const String _modeKey = 'riceai_server_mode';
  static String _localBaseUrl = _buildBaseUrl;
  static String _internetBaseUrl = '';
  static RiceAiServerMode _mode = RiceAiServerMode.local;

  static RiceAiServerMode get mode => _mode;
  static String get apiBaseUrl => addressFor(_mode);
  static String addressFor(RiceAiServerMode mode) =>
      mode == RiceAiServerMode.local ? _localBaseUrl : _internetBaseUrl;

  static Future<void> load() async {
    try {
      final preferences = await SharedPreferences.getInstance();
      final local = preferences.getString(_localKey) ??
          preferences.getString(_legacyKey) ??
          _buildBaseUrl;
      final internet = preferences.getString(_internetKey) ?? '';
      _localBaseUrl = isValidServerUrl(local, RiceAiServerMode.local)
          ? normalize(local)
          : _buildBaseUrl;
      _internetBaseUrl = isValidServerUrl(internet, RiceAiServerMode.internet)
          ? normalize(internet)
          : '';
      _mode = preferences.getString(_modeKey) == 'internet' &&
              _internetBaseUrl.isNotEmpty
          ? RiceAiServerMode.internet
          : RiceAiServerMode.local;
    } catch (_) {
      _localBaseUrl = _buildBaseUrl;
      _internetBaseUrl = '';
      _mode = RiceAiServerMode.local;
    }
  }

  static String normalize(String value) =>
      value.trim().replaceFirst(RegExp(r'/$'), '');

  static bool isValidServerUrl(String value, RiceAiServerMode mode) {
    final uri = Uri.tryParse(normalize(value));
    if (uri == null ||
        uri.host.isEmpty ||
        uri.path.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.userInfo.isNotEmpty) {
      return false;
    }
    if (mode == RiceAiServerMode.internet) {
      return uri.scheme == 'https' &&
          (!uri.hasPort || (uri.port > 0 && uri.port <= 65535));
    }
    return uri.scheme == 'http' &&
        uri.hasPort &&
        uri.port > 0 &&
        uri.port <= 65535;
  }

  static Future<void> saveForMode(RiceAiServerMode mode, String value) async {
    final normalized = normalize(value);
    if (!isValidServerUrl(normalized, mode)) {
      throw FormatException(mode == RiceAiServerMode.local
          ? 'Nhập địa chỉ dạng http://IP:8015'
          : 'Nhập địa chỉ HTTPS của máy chủ Internet');
    }
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(
        mode == RiceAiServerMode.local ? _localKey : _internetKey, normalized);
    await preferences.setString(
        _modeKey, mode == RiceAiServerMode.local ? 'local' : 'internet');
    if (mode == RiceAiServerMode.local) {
      _localBaseUrl = normalized;
    } else {
      _internetBaseUrl = normalized;
    }
    _mode = mode;
  }

  static bool get isApiConfigured => apiBaseUrl.isNotEmpty;

  static String get displayBaseUrl =>
      isApiConfigured ? apiBaseUrl : 'Chưa cấu hình máy chủ';
}
