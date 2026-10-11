import 'dart:io';

import 'package:flutter/material.dart';

import '../../core/config/environment_config.dart';
import '../../core/config/seven_class_catalog.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/server_time.dart';
import '../../models/offline_queue_item.dart';
import '../../services/offline_queue_service.dart';
import '../../services/prediction_service.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final _predictionService = PredictionService();
  final _queueService = OfflineQueueService();
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _history = const <Map<String, dynamic>>[];
  List<OfflineQueueItem> _queue = const <OfflineQueueItem>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    List<Map<String, dynamic>> history = const <Map<String, dynamic>>[];
    List<OfflineQueueItem> queue = const <OfflineQueueItem>[];
    String? error;

    try {
      history = await _predictionService.getHistory();
    } catch (_) {
      error =
          'Không tải được lịch sử từ máy chủ. Bạn vẫn có thể xem ảnh chờ gửi.';
    }
    try {
      queue = await _queueService.getQueue();
    } catch (_) {
      error ??= 'Không đọc được ảnh chờ gửi trên thiết bị.';
    }
    if (!mounted) return;
    setState(() {
      _history = history;
      _queue = queue;
      _error = error;
      _loading = false;
    });
  }

  Future<void> _deleteQueueItem(OfflineQueueItem item) async {
    await _queueService.deleteItem(item);
    await _load();
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 2,
        child: Scaffold(
          backgroundColor: AppTheme.porcelain,
          appBar: AppBar(
            title: const Text('Lịch sử quét'),
            actions: <Widget>[
              IconButton(
                onPressed: _loading ? null : _load,
                icon: const Icon(Icons.refresh_rounded),
                tooltip: 'Tải lại',
              ),
            ],
            bottom: const TabBar(
              tabs: <Widget>[
                Tab(text: 'Đã phân tích'),
                Tab(text: 'Chờ gửi'),
              ],
            ),
          ),
          body: _loading
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: <Widget>[
                    if (_error != null)
                      _ConnectionNotice(message: _error!, onRetry: _load),
                    Expanded(
                      child: TabBarView(
                        children: <Widget>[
                          _HistoryList(items: _history),
                          _QueueList(items: _queue, onDelete: _deleteQueueItem),
                        ],
                      ),
                    ),
                  ],
                ),
        ),
      );
}

class _HistoryList extends StatelessWidget {
  const _HistoryList({required this.items});
  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const _EmptyState(
        icon: Icons.history_rounded,
        title: 'Chưa có lịch sử quét',
        subtitle: 'Các lượt phân tích thành công sẽ xuất hiện ở đây.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, index) => _HistoryTile(item: items[index]),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.item});
  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final filename = item['image_filename']?.toString();
    final confidence = (item['confidence'] as num?)?.toDouble();
    final createdAt = parseServerTime(item['created_at']);
    final classId = item['prediction']?.toString() ?? '';
    final confidenceText =
        confidence == null || classId == 'uncertain'
            ? 'Chưa kết luận'
            : '${(confidence * 100).toStringAsFixed(1)}%';
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.cardSolid,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.borderBeige),
      ),
      child: Row(
        children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(11),
            child: SizedBox(
              width: 58,
              height: 58,
              child: filename == null
                  ? const ColoredBox(color: AppTheme.cardBeige)
                  : Image.network(
                      '${EnvironmentConfig.apiBaseUrl}/uploads/$filename',
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const ColoredBox(
                        color: AppTheme.cardBeige,
                        child: Icon(Icons.image_not_supported_outlined),
                      ),
                    ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  SevenClassCatalog.names[classId] ?? 'Không xác định',
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 3),
                Text(
                  '$confidenceText · ${_dateText(createdAt)}',
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _dateText(DateTime? value) {
    if (value == null) return 'Không rõ thời gian';
    return '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}';
  }
}

class _QueueList extends StatelessWidget {
  const _QueueList({required this.items, required this.onDelete});
  final List<OfflineQueueItem> items;
  final ValueChanged<OfflineQueueItem> onDelete;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const _EmptyState(
        icon: Icons.cloud_done_outlined,
        title: 'Không có ảnh chờ gửi',
        subtitle: 'Khi mất mạng, ảnh sẽ được lưu an toàn và gửi lại sau.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, index) {
        final item = items[index];
        return ListTile(
          leading: ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child: Image.file(
              File(item.localPath),
              width: 48,
              height: 48,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) =>
                  const Icon(Icons.broken_image_outlined),
            ),
          ),
          title: Text(item.analysisMode == 'plus'
              ? 'Plus · Agri-CAM'
              : 'Basic · Grad-CAM'),
          subtitle: Text('Đã thử gửi ${item.retryCount} lần'),
          trailing: IconButton(
            onPressed: () => onDelete(item),
            icon: const Icon(Icons.delete_outline_rounded),
            tooltip: 'Xóa ảnh chờ gửi',
          ),
        );
      },
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState(
      {required this.icon, required this.title, required this.subtitle});
  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(icon, size: 44, color: AppTheme.moss),
              const SizedBox(height: 12),
              Text(title,
                  style: const TextStyle(
                      fontWeight: FontWeight.w900, fontSize: 17)),
              const SizedBox(height: 6),
              Text(subtitle,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: AppTheme.textSecondary, height: 1.4)),
            ],
          ),
        ),
      );
}

class _ConnectionNotice extends StatelessWidget {
  const _ConnectionNotice({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
        padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
        decoration: BoxDecoration(
          color: AppTheme.warningOrange.withValues(alpha: .1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: <Widget>[
            const Icon(Icons.cloud_off_rounded,
                color: AppTheme.warningOrange, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text(message,
                  style: const TextStyle(fontSize: 12, height: 1.35)),
            ),
            IconButton(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              tooltip: 'Thử lại',
            ),
          ],
        ),
      );
}
