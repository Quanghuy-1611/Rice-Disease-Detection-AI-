import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mobile_app/core/config/environment_config.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('local addresses require HTTP and an explicit port', () {
    expect(
        EnvironmentConfig.isValidServerUrl(
            'http://172.20.10.2:8015', RiceAiServerMode.local),
        isTrue);
    expect(
        EnvironmentConfig.isValidServerUrl(
            'https://172.20.10.2:8015', RiceAiServerMode.local),
        isFalse);
    expect(
        EnvironmentConfig.isValidServerUrl(
            'http://172.20.10.2', RiceAiServerMode.local),
        isFalse);
    expect(
        EnvironmentConfig.isValidServerUrl(
            'http://172.20.10.2:8015/path', RiceAiServerMode.local),
        isFalse);
  });

  test('Internet addresses require HTTPS', () {
    expect(
        EnvironmentConfig.isValidServerUrl(
            'https://api.riceai.example', RiceAiServerMode.internet),
        isTrue);
    expect(
        EnvironmentConfig.isValidServerUrl(
            'http://api.riceai.example:8015', RiceAiServerMode.internet),
        isFalse);
    expect(
        EnvironmentConfig.isValidServerUrl(
            'https://api.riceai.example/path', RiceAiServerMode.internet),
        isFalse);
  });

  test('stores local and Internet addresses independently', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await EnvironmentConfig.load();
    await EnvironmentConfig.saveForMode(
        RiceAiServerMode.local, 'http://172.20.10.2:8015/');
    await EnvironmentConfig.saveForMode(
        RiceAiServerMode.internet, 'https://api.riceai.example/');
    await EnvironmentConfig.load();
    expect(EnvironmentConfig.mode, RiceAiServerMode.internet);
    expect(EnvironmentConfig.apiBaseUrl, 'https://api.riceai.example');
    expect(EnvironmentConfig.addressFor(RiceAiServerMode.local),
        'http://172.20.10.2:8015');
  });

  test('migrates the previously saved laptop address', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'riceai_api_base_url': 'http://192.168.100.155:8015',
    });
    await EnvironmentConfig.load();
    expect(EnvironmentConfig.mode, RiceAiServerMode.local);
    expect(EnvironmentConfig.apiBaseUrl, 'http://192.168.100.155:8015');
  });
}
