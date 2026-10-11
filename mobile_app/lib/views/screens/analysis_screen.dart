import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../../core/errors/api_exception.dart';
import '../../core/theme/app_theme.dart';
import '../../services/connectivity_service.dart';
import '../../services/image_processing_service.dart';
import '../../services/image_quality_service.dart';
import '../../services/notification_service.dart';
import '../../services/offline_queue_service.dart';
import '../../services/prediction_service.dart';
import 'result_screen.dart';

enum AnalysisState {
  ready,
  checking,
  processing,
  uploading,
  queued,
  error,
  success
}

class AnalysisScreen extends StatefulWidget {
  const AnalysisScreen({
    super.key,
    required this.imageFile,
    this.analysisMode = 'basic',
  });

  final File imageFile;
  final String analysisMode;

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen>
    with SingleTickerProviderStateMixin {
  final _predictionService = PredictionService();
  final _qualityService = ImageQualityService();
  final _processingService = ImageProcessingService();
  final _queueService = OfflineQueueService();
  final _connectivityService = ConnectivityService();

  late final AnimationController _scannerController;
  AnalysisState _state = AnalysisState.ready;
  String _status = 'Ảnh đã sẵn sàng';
  String _severity = 'low';
  bool _inFlight = false;

  @override
  void initState() {
    super.initState();
    _scannerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    if (widget.analysisMode == 'plus') {
      WidgetsBinding.instance.addPostFrameCallback((_) => _runAnalysis());
    }
  }

  Future<void> _runAnalysis({bool skipQualityWarning = false}) async {
    if (_inFlight) return;
    _inFlight = true;
    _scannerController.repeat(reverse: true);
    File? processedFile;
    var queued = false;
    try {
      _setState(AnalysisState.checking, 'Đang kiểm tra chất lượng ảnh...');
      final quality = await _qualityService.checkQuality(widget.imageFile);
      if (!quality.isAcceptable && !skipQualityWarning) {
        _scannerController.stop();
        final continueAnalysis = await _showQualityDialog(quality);
        if (!continueAnalysis) {
          if (mounted) Navigator.of(context).pop();
          return;
        }
        _scannerController.repeat(reverse: true);
      }

      _setState(
          AnalysisState.processing, 'Đang nén ảnh để tiết kiệm dữ liệu...');
      final processed = await _processingService.processImage(widget.imageFile);
      processedFile = processed.file;

      if (!await _connectivityService.isConnected) {
        await _queueService.addToQueue(
          processedFile,
          widget.analysisMode,
          severity: _severity,
        );
        queued = true;
        _setState(AnalysisState.queued, 'Đã lưu ảnh, sẽ gửi khi có mạng.');
        _scannerController.stop();
        return;
      }

      _setState(AnalysisState.uploading, 'Đang gửi ảnh đến AI...');
      final result = await _predictionService.predictImage(
        processedFile,
        analysisMode: widget.analysisMode,
        severity: _severity,
      );
      if (result['success'] != true) {
        throw ApiException(
            message: 'Máy chủ chưa thể hoàn tất lượt phân tích.');
      }
      _setState(AnalysisState.success, 'Hoàn tất phân tích.');
      result['observed_severity'] = _severity;
      if (!mounted) return;
      await context.read<NotificationService>().addPrediction(
            disease: result['prediction']?.toString() ?? 'Không xác định',
            confidence: (result['confidence'] as num?)?.toDouble() ?? 0,
          );
      _scannerController.stop();
      if (!mounted) return;
      await Future<void>.delayed(const Duration(milliseconds: 350));
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        PageRouteBuilder<void>(
          pageBuilder: (_, __, ___) => ResultScreen(
            predictionData: result,
            imageFile: widget.imageFile,
          ),
          transitionsBuilder: (_, animation, __, child) =>
              FadeTransition(opacity: animation, child: child),
        ),
      );
    } on ApiException catch (error) {
      if (error.statusCode == null && processedFile != null) {
        await _queueService.addToQueue(
          processedFile,
          widget.analysisMode,
          severity: _severity,
        );
        queued = true;
        _setState(AnalysisState.queued, 'Đã lưu ảnh, sẽ gửi khi có mạng.');
      } else {
        _setState(AnalysisState.error, error.message);
      }
      _scannerController.stop();
    } on FormatException catch (error) {
      _setState(AnalysisState.error, error.message);
      _scannerController.stop();
    } catch (_) {
      _setState(AnalysisState.error, 'Không thể xử lý ảnh. Vui lòng thử lại.');
      _scannerController.stop();
    } finally {
      _inFlight = false;
      if (!queued && processedFile != null && await processedFile.exists()) {
        await processedFile.delete();
      }
    }
  }

  Future<bool> _showQualityDialog(ImageQualityResult quality) async {
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        icon: const Icon(Icons.photo_camera_back_outlined,
            color: AppTheme.warningOrange),
        title: const Text('Kiểm tra ảnh'),
        content: Text(
            '${quality.message}\n\nBạn vẫn muốn gửi ảnh này để phân tích chứ?'),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Chụp lại'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Vẫn tiếp tục'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  void _setState(AnalysisState state, String status) {
    if (!mounted) return;
    setState(() {
      _state = state;
      _status = status;
    });
  }

  @override
  void dispose() {
    _scannerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final canRetry = _state == AnalysisState.error;
    final isReady = _state == AnalysisState.ready;
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        leading: IconButton(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.close_rounded),
          tooltip: 'Huỷ phân tích',
        ),
        title: Text(widget.analysisMode == 'plus'
            ? 'Phân tích Plus'
            : 'Phân tích Basic'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          children: <Widget>[
            _ScanningImage(
              imageFile: widget.imageFile,
              animation: _scannerController,
              height: isReady ? 220 : 310,
              showLaser: _state == AnalysisState.checking ||
                  _state == AnalysisState.processing ||
                  _state == AnalysisState.uploading,
            ).animate().fade().scale(begin: const Offset(0.96, 0.96)),
            SizedBox(height: isReady ? 20 : 34),
            _StatusIcon(state: _state),
            const SizedBox(height: 14),
            Text(
              _status,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              isReady
                  ? 'Chọn mức độ bạn quan sát tại ruộng trước khi phân tích.'
                  : widget.analysisMode == 'plus'
                      ? 'Plus đối chiếu nhiều mô hình trước khi đưa ra kết luận.'
                      : 'Basic dùng Grad-CAM để giải thích dự đoán.',
              textAlign: TextAlign.center,
              style:
                  const TextStyle(color: AppTheme.textSecondary, height: 1.4),
            ),
            if (isReady) ...<Widget>[
              const SizedBox(height: 24),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.cardSolid,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: AppTheme.borderBeige),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text(
                      'Mức độ quan sát trên ruộng',
                      style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 5),
                    const Text(
                      'Chỉ dùng để gợi ý xử lý; đây không phải mức độ AI đo từ ảnh.',
                      style: TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        _severityChoice('low', 'Ít / Thấp'),
                        _severityChoice('medium', 'Trung bình'),
                        _severityChoice('high', 'Cao'),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _runAnalysis,
                  icon: const Icon(Icons.auto_awesome_rounded),
                  label: const Text('Phân tích ảnh'),
                ),
              ),
            ],
            if (canRetry) ...<Widget>[
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _runAnalysis,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Thử lại'),
              ),
            ],
            if (_state == AnalysisState.queued) ...<Widget>[
              const SizedBox(height: 24),
              OutlinedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Quay lại trang chủ'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _severityChoice(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _severity == value,
        onSelected: (_) => setState(() => _severity = value),
        selectedColor: AppTheme.moss.withValues(alpha: 0.14),
        labelStyle: TextStyle(
          color: _severity == value ? AppTheme.moss : AppTheme.textSecondary,
          fontWeight: FontWeight.w700,
        ),
        side: BorderSide(
          color: _severity == value ? AppTheme.moss : AppTheme.borderBeige,
        ),
      );
}

class _ScanningImage extends StatelessWidget {
  const _ScanningImage({
    required this.imageFile,
    required this.animation,
    required this.height,
    required this.showLaser,
  });

  final File imageFile;
  final Animation<double> animation;
  final double height;
  final bool showLaser;

  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: AnimatedBuilder(
          animation: animation,
          builder: (_, __) => Stack(
            children: <Widget>[
              Image.file(imageFile,
                  height: height, width: double.infinity, fit: BoxFit.cover),
              if (showLaser)
                Positioned(
                  top: height * animation.value,
                  left: 0,
                  right: 0,
                  child: Container(
                    height: 3,
                    color: AppTheme.neonLeaf,
                  ),
                ),
            ],
          ),
        ),
      );
}

class _StatusIcon extends StatelessWidget {
  const _StatusIcon({required this.state});
  final AnalysisState state;

  @override
  Widget build(BuildContext context) => switch (state) {
        AnalysisState.ready => const Icon(
            Icons.photo_library_outlined,
            color: AppTheme.moss,
            size: 28,
          ),
        AnalysisState.checking ||
        AnalysisState.processing ||
        AnalysisState.uploading =>
          const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 3),
          ),
        AnalysisState.queued => const Icon(Icons.cloud_queue_rounded,
            color: AppTheme.warningOrange, size: 28),
        AnalysisState.error => const Icon(Icons.error_outline_rounded,
            color: AppTheme.errorRed, size: 28),
        AnalysisState.success => const Icon(Icons.check_circle_rounded,
            color: AppTheme.safeGreen, size: 28),
      };
}
