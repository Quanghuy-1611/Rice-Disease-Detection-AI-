class OfflineQueueItem {
  const OfflineQueueItem({
    this.id,
    required this.localPath,
    required this.analysisMode,
    this.severity = 'low',
    required this.createdAt,
    this.retryCount = 0,
    this.status = 'pending',
  });

  final int? id;
  final String localPath;
  final String analysisMode;
  final String severity;
  final DateTime createdAt;
  final int retryCount;
  final String status;

  Map<String, Object?> toMap() => <String, Object?>{
        'id': id,
        'local_path': localPath,
        'analysis_mode': analysisMode,
        'severity': severity,
        'created_at': createdAt.toIso8601String(),
        'retry_count': retryCount,
        'status': status,
      };

  factory OfflineQueueItem.fromMap(Map<String, Object?> map) =>
      OfflineQueueItem(
        id: map['id'] as int?,
        localPath: map['local_path']! as String,
        analysisMode: map['analysis_mode']! as String,
        severity: (map['severity'] as String?) ?? 'low',
        createdAt: DateTime.parse(map['created_at']! as String),
        retryCount: (map['retry_count'] as int?) ?? 0,
        status: (map['status'] as String?) ?? 'pending',
      );
}
