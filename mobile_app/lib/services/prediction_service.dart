import 'dart:io';

import 'package:dio/dio.dart';

import '../core/network/api_client.dart';
import '../core/errors/api_exception.dart';

DioMediaType _imageMediaType(String path) {
  final lower = path.toLowerCase();
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
    return DioMediaType('image', 'jpeg');
  }
  if (lower.endsWith('.png')) return DioMediaType('image', 'png');
  if (lower.endsWith('.webp')) return DioMediaType('image', 'webp');
  throw ApiException(message: 'Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.');
}

class PredictionService {
  final ApiClient _apiClient = ApiClient();

  Future<Map<String, dynamic>> getPlan() async {
    final response = await _apiClient.get('/api/plans/me');
    return Map<String, dynamic>.from(response as Map);
  }

  Future<bool> isPlusReady() async {
    final response = await _apiClient.get('/api/plans/catalog');
    return response is Map && response['plus_ready'] == true;
  }

  Future<Map<String, dynamic>> predictPlus(List<File> images) async {
    if (images.isEmpty || images.length > 5) {
      throw ArgumentError('Plus nhận từ 1 đến 5 ảnh.');
    }
    final form = FormData();
    for (final image in images) {
      form.files.add(MapEntry(
          'files',
          await MultipartFile.fromFile(image.path,
              filename: image.path.split(Platform.pathSeparator).last,
              contentType: _imageMediaType(image.path))));
    }
    final response = await _apiClient.post('/api/predict/plus',
        data: form, receiveTimeout: const Duration(minutes: 2));
    return Map<String, dynamic>.from(response as Map);
  }

  Future<Map<String, dynamic>> predictImage(
    File image, {
    String analysisMode = 'basic',
    String severity = 'low',
  }) async {
    final formData = FormData.fromMap(<String, dynamic>{
      'file': await MultipartFile.fromFile(
        image.path,
        filename: image.path.split(Platform.pathSeparator).last,
        contentType: _imageMediaType(image.path),
      ),
      'analysis_mode': analysisMode,
      'severity': severity,
    });

    final response = await _apiClient.post('/api/predict', data: formData);
    return Map<String, dynamic>.from(response as Map);
  }

  Future<List<Map<String, dynamic>>> getHistory() async {
    final response = await _apiClient.get('/api/history');
    if (response is! List) return const <Map<String, dynamic>>[];
    return response
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
}
