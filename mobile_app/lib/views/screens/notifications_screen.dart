import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/notification_service.dart';
import '../widgets/app_card.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final notifications = context.watch<NotificationService>();
    final items = notifications.items;
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        title: const Text('Thông báo'),
        actions: <Widget>[
          if (items.isNotEmpty)
            TextButton(
              onPressed: notifications.markAllRead,
              child: const Text('Đã đọc hết'),
            ),
        ],
      ),
      body: !notifications.isLoaded
          ? const Center(child: CircularProgressIndicator(color: AppTheme.moss))
          : items.isEmpty
              ? const _EmptyNotifications()
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(20, 14, 20, 32),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return Dismissible(
                      key: ValueKey(item.id),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 24),
                        decoration: BoxDecoration(
                            color: AppTheme.dangerRed,
                            borderRadius: BorderRadius.circular(20)),
                        child: const Icon(Icons.delete_outline_rounded,
                            color: Colors.white),
                      ),
                      onDismissed: (_) => notifications.remove(item.id),
                      child: AppCard(
                        color: item.isRead
                            ? AppTheme.cardSolid
                            : AppTheme.cardBeige,
                        child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Container(
                                width: 42,
                                height: 42,
                                decoration: BoxDecoration(
                                    color: AppTheme.moss.withValues(alpha: .12),
                                    borderRadius: BorderRadius.circular(13)),
                                child: const Icon(Icons.analytics_outlined,
                                    color: AppTheme.moss),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                  child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: <Widget>[
                                    Text(item.title,
                                        style: TextStyle(
                                            fontWeight: item.isRead
                                                ? FontWeight.w700
                                                : FontWeight.w900)),
                                    const SizedBox(height: 4),
                                    Text(item.message,
                                        style: const TextStyle(
                                            color: AppTheme.textSecondary,
                                            height: 1.4)),
                                    const SizedBox(height: 7),
                                    Text(_formatTime(item.createdAt),
                                        style: const TextStyle(
                                            fontSize: 11,
                                            color: AppTheme.textMuted)),
                                  ])),
                              if (!item.isRead)
                                Container(
                                    width: 8,
                                    height: 8,
                                    decoration: const BoxDecoration(
                                        color: AppTheme.neonLeaf,
                                        shape: BoxShape.circle)),
                            ]),
                      ),
                    );
                  },
                ),
    );
  }

  String _formatTime(DateTime time) {
    final difference = DateTime.now().difference(time);
    if (difference.inMinutes < 1) return 'Vừa xong';
    if (difference.inHours < 1) return '${difference.inMinutes} phút trước';
    if (difference.inDays < 1) return '${difference.inHours} giờ trước';
    return '${time.day.toString().padLeft(2, '0')}/${time.month.toString().padLeft(2, '0')}/${time.year}';
  }
}

class _EmptyNotifications extends StatelessWidget {
  const _EmptyNotifications();
  @override
  Widget build(BuildContext context) => const Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Icon(Icons.notifications_none_rounded,
              size: 50, color: AppTheme.textMuted),
          SizedBox(height: 12),
          Text('Chưa có thông báo',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
          SizedBox(height: 6),
          Text('Kết quả phân tích mới sẽ xuất hiện tại đây.',
              style: TextStyle(color: AppTheme.textSecondary)),
        ]),
      );
}
