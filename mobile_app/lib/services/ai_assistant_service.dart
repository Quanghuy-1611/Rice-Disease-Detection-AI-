import '../core/network/api_client.dart';

class AiAssistantService {
  final ApiClient _apiClient = ApiClient();

  Future<Map<String, dynamic>> askQuestion(String message) async {
    final response = await _apiClient.post(
      '/api/chat/ask',
      data: <String, dynamic>{'message': message},
    );
    if (response is Map<String, dynamic> && response['reply'] is String) {
      return response;
    }
    throw Exception('Máy chủ trả về phản hồi trợ lý không hợp lệ.');
  }
}
