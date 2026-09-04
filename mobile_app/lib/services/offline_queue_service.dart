import 'dart:io';

import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../models/offline_queue_item.dart';
import 'prediction_service.dart';

class QueueSyncResult {
  const QueueSyncResult({required this.sent, required this.failed});

  final int sent;
  final int failed;
}

class OfflineQueueService {
  static const _databaseName = 'riceai_offline_queue.db';
  static const _table = 'offline_predictions';
  Database? _database;
  bool _syncing = false;

  Future<Database> get _db async {
    final existing = _database;
    if (existing != null) return existing;
    final databasePath = path.join(await getDatabasesPath(), _databaseName);
    _database = await openDatabase(
      databasePath,
      version: 1,
      onCreate: (database, version) async {
        await database.execute('''
          CREATE TABLE $_table(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_path TEXT NOT NULL,
            analysis_mode TEXT NOT NULL,
            created_at TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending'
          )
        ''');
      },
    );
    return _database!;
  }

  Future<OfflineQueueItem> addToQueue(File processedFile, String analysisMode) async {
    final documents = await getApplicationDocumentsDirectory();
    final queueDirectory = Directory(path.join(documents.path, 'riceai_offline_queue'));
    await queueDirectory.create(recursive: true);
    final destination = File(path.join(
      queueDirectory.path,
      'queue_${DateTime.now().microsecondsSinceEpoch}.jpg',
    ));
    await processedFile.copy(destination.path);
    final item = OfflineQueueItem(
      localPath: destination.path,
      analysisMode: analysisMode,
      createdAt: DateTime.now().toUtc(),
    );
    final id = await (await _db).insert(_table, item.toMap()..remove('id'));
    return OfflineQueueItem(
      id: id,
      localPath: item.localPath,
      analysisMode: item.analysisMode,
      createdAt: item.createdAt,
    );
  }

  Future<List<OfflineQueueItem>> getQueue() async {
    final rows = await (await _db).query(_table, orderBy: 'created_at DESC');
    return rows
        .map((row) => OfflineQueueItem.fromMap(Map<String, Object?>.from(row)))
        .toList();
  }

  Future<QueueSyncResult> retryPending({PredictionService? predictionService}) async {
    if (_syncing) return const QueueSyncResult(sent: 0, failed: 0);
    _syncing = true;
    var sent = 0;
    var failed = 0;
    final predictor = predictionService ?? PredictionService();
    try {
      for (final item in await getQueue()) {
        final file = File(item.localPath);
        if (!await file.exists()) {
          await _deleteRecord(item.id);
          continue;
        }
        try {
          final result = await predictor.predictImage(
            file,
            analysisMode: item.analysisMode,
          );
          if (result['success'] == true) {
            await _deleteRecord(item.id);
            await file.delete();
            sent++;
          } else {
            await _markRetry(item);
            failed++;
          }
        } catch (_) {
          await _markRetry(item);
          failed++;
        }
      }
    } finally {
      _syncing = false;
    }
    return QueueSyncResult(sent: sent, failed: failed);
  }

  Future<void> deleteItem(OfflineQueueItem item) async {
    await _deleteRecord(item.id);
    final file = File(item.localPath);
    if (await file.exists()) await file.delete();
  }

  Future<void> _markRetry(OfflineQueueItem item) async {
    if (item.id == null) return;
    await (await _db).update(
      _table,
      <String, Object?>{
        'retry_count': item.retryCount + 1,
        'status': 'pending',
      },
      where: 'id = ?',
      whereArgs: <Object?>[item.id],
    );
  }

  Future<void> _deleteRecord(int? id) async {
    if (id == null) return;
    await (await _db).delete(_table, where: 'id = ?', whereArgs: <Object?>[id]);
  }
}
