import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Chat history is local to this device and scoped to the Firebase account.
class ChatHistoryStore {
  const ChatHistoryStore();

  String _key(String accountId) => 'riceai_chat_history_v1_$accountId';

  Future<List<Map<String, dynamic>>> load(String? accountId) async {
    if (accountId == null) return <Map<String, dynamic>>[];
    final preferences = await SharedPreferences.getInstance();
    try {
      final decoded =
          jsonDecode(preferences.getString(_key(accountId)) ?? '[]');
      if (decoded is! List) return <Map<String, dynamic>>[];
      return decoded
          .whereType<Map>()
          .where((message) =>
              message['text'] is String &&
              (message['isUser'] == true || message['isUser'] == false))
          .map((message) => Map<String, dynamic>.from(message))
          .take(100)
          .toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  Future<void> save(
      String? accountId, List<Map<String, dynamic>> messages) async {
    if (accountId == null) return;
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(
      _key(accountId),
      jsonEncode(messages.take(100).toList()),
    );
  }
}
