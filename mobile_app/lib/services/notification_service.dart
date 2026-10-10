import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/app_notification.dart';
import '../core/config/seven_class_catalog.dart';

/// Hộp thư thông báo nội bộ: chỉ lưu sự kiện thật phát sinh từ app.
class NotificationService extends ChangeNotifier {
  static const _storageKey = 'riceai_notifications_v1';
  List<AppNotification> _items = const <AppNotification>[];
  bool _loaded = false;

  List<AppNotification> get items => List<AppNotification>.unmodifiable(_items);
  int get unreadCount => _items.where((item) => !item.isRead).length;
  bool get isLoaded => _loaded;

  NotificationService() {
    load();
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_storageKey);
    if (raw != null) {
      try {
        final decoded = jsonDecode(raw) as List<dynamic>;
        _items = decoded
            .whereType<Map>()
            .map((json) =>
                AppNotification.fromJson(Map<String, dynamic>.from(json)))
            .toList()
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      } catch (_) {
        _items = const <AppNotification>[];
      }
    }
    _loaded = true;
    notifyListeners();
  }

  Future<void> addPrediction(
      {required String disease, required double confidence}) async {
    final diseaseName = SevenClassCatalog.names[disease] ?? disease;
    await _add(
      title: 'Phân tích đã hoàn tất',
      message:
          'Kết quả nhận diện: $diseaseName (${(confidence * 100).toStringAsFixed(1)}%).',
      type: 'prediction',
    );
  }

  Future<void> addQueueSynced({required int count}) async {
    if (count <= 0) return;
    await _add(
      title: 'Đã gửi ảnh chờ phân tích',
      message: count == 1
          ? 'Một ảnh đã được gửi lại thành công khi có mạng.'
          : '$count ảnh đã được gửi lại thành công khi có mạng.',
      type: 'queue_sync',
    );
  }

  Future<void> markAllRead() async {
    _items = _items.map((item) => item.copyWith(isRead: true)).toList();
    await _persist();
    notifyListeners();
  }

  Future<void> remove(String id) async {
    _items = _items.where((item) => item.id != id).toList();
    await _persist();
    notifyListeners();
  }

  Future<void> clear() async {
    _items = const <AppNotification>[];
    await _persist();
    notifyListeners();
  }

  Future<void> _add(
      {required String title,
      required String message,
      required String type}) async {
    _items = <AppNotification>[
      AppNotification(
        id: '${DateTime.now().microsecondsSinceEpoch}-$type',
        title: title,
        message: message,
        createdAt: DateTime.now(),
        isRead: false,
        type: type,
      ),
      ..._items,
    ].take(100).toList();
    await _persist();
    notifyListeners();
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        _storageKey, jsonEncode(_items.map((item) => item.toJson()).toList()));
  }
}
