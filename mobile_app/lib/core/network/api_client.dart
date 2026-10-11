import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../config/environment_config.dart';
import '../errors/api_exception.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String _appVersion = 'unknown';

  ApiClient._internal() {
    PackageInfo.fromPlatform().then((info) {
      _appVersion = '${info.version}+${info.buildNumber}';
    }).catchError((_) {});
    _dio = Dio(
      BaseOptions(
        baseUrl: EnvironmentConfig.apiBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          HttpHeaders.contentTypeHeader: 'application/json',
        },
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Attach JWT token if available
          final token = await _storage.read(key: 'jwt_token');
          if (token != null) {
            options.headers[HttpHeaders.authorizationHeader] = 'Bearer $token';
          }
          options.headers['X-RiceAI-Client'] =
              Platform.isIOS ? 'ios' : 'android';
          options.headers['X-RiceAI-Version'] = _appVersion;
          return handler.next(options);
        },
        onResponse: (response, handler) {
          return handler.next(response);
        },
        onError: (DioException e, handler) {
          return handler.next(e);
        },
      ),
    );
  }

  Dio get dio => _dio;
  Future<String> getAppVersion() async {
    if (_appVersion == 'unknown') {
      try {
        final info = await PackageInfo.fromPlatform();
        _appVersion = '${info.version}+${info.buildNumber}';
      } catch (_) {}
    }
    return _appVersion;
  }

  /// Helper method for GET requests
  Future<dynamic> get(String path,
      {Map<String, dynamic>? queryParameters}) async {
    _ensureConfigured();
    try {
      final response = await _dio.get(path, queryParameters: queryParameters);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Helper method for POST requests
  Future<dynamic> post(String path,
      {dynamic data,
      Map<String, dynamic>? queryParameters,
      Duration? receiveTimeout}) async {
    _ensureConfigured();
    try {
      final response = await _dio.post(path,
          data: data,
          queryParameters: queryParameters,
          options: Options(receiveTimeout: receiveTimeout));
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<dynamic> put(String path, {dynamic data}) async {
    _ensureConfigured();
    try {
      final response = await _dio.put(path, data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  ApiException _handleDioError(DioException e) {
    if (e.response != null) {
      final statusCode = e.response?.statusCode;
      final friendlyMessage = switch (statusCode) {
        401 || 403 => 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
        408 => 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.',
        final code? when code >= 500 =>
          'Đang có nhiều ảnh chờ phân tích. Vui lòng thử lại sau vài giây.',
        _ => _extractErrorMessage(e.response?.data),
      };
      return ApiException(
        statusCode: statusCode,
        message: friendlyMessage ?? 'Yêu cầu không hợp lệ. Vui lòng thử lại.',
        data: e.response?.data,
      );
    } else {
      final message = switch (e.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.receiveTimeout ||
        DioExceptionType.sendTimeout =>
          'Kết nối máy chủ quá lâu. Vui lòng thử lại.',
        DioExceptionType.connectionError =>
          'Không kết nối được máy chủ. Kiểm tra mạng và thử lại.',
        _ => 'Không kết nối được máy chủ. Kiểm tra mạng và thử lại.',
      };
      return ApiException(
        message: message,
      );
    }
  }

  String? _extractErrorMessage(dynamic data) {
    if (data is Map<String, dynamic>) {
      if (data.containsKey('detail')) {
        return data['detail'].toString();
      }
      if (data.containsKey('message')) {
        return data['message'].toString();
      }
    }
    return null;
  }

  void _ensureConfigured() {
    if (!EnvironmentConfig.isApiConfigured) {
      throw ApiException(
        statusCode: -1,
        message:
            'Chưa cấu hình địa chỉ máy chủ. Hãy chạy ứng dụng với API_BASE_URL.',
      );
    }
  }
}
