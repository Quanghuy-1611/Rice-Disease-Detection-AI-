import 'dart:io';

import 'package:dio/dio.dart';

import '../core/network/api_client.dart';

class PredictionService {
  final ApiClient _apiClient = ApiClient();

  Future<Map<String, dynamic>> predictImage(
    File image, {
    String analysisMode = 'basic',
    String severity = 'low',
  }) async {
    final formData = FormData.fromMap(<String, dynamic>{
      'file': await MultipartFile.fromFile(
        image.path,
        filename: image.path.split(Platform.pathSeparator).last,
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
