import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/offline_queue_item.dart';

void main() {
  test('keeps the observed severity when an offline item is restored', () {
    final item = OfflineQueueItem(
      localPath: 'queued.jpg',
      analysisMode: 'basic',
      severity: 'high',
      createdAt: DateTime.utc(2026, 10, 11),
    );

    expect(OfflineQueueItem.fromMap(item.toMap()).severity, 'high');
  });

  test('older queued items default to low severity', () {
    final restored = OfflineQueueItem.fromMap({
      'local_path': 'queued.jpg',
      'analysis_mode': 'basic',
      'created_at': '2026-10-11T00:00:00Z',
    });

    expect(restored.severity, 'low');
  });
}
