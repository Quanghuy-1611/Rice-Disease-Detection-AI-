import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';

import '../../core/config/environment_config.dart';
import '../../core/theme/app_theme.dart';

/// Keeps the selected photo visible while a result image arrives over a slow network.
class ReliableResultImage extends StatefulWidget {
  const ReliableResultImage({
    super.key,
    required this.path,
    this.localFallback,
    this.width = double.infinity,
    this.height,
    this.fit = BoxFit.cover,
  });

  final String path;
  final File? localFallback;
  final double width;
  final double? height;
  final BoxFit fit;

  @override
  State<ReliableResultImage> createState() => _ReliableResultImageState();
}

class _ReliableResultImageState extends State<ReliableResultImage> {
  int _attempt = 0;
  Timer? _automaticRetry;

  @override
  void didUpdateWidget(covariant ReliableResultImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.path != widget.path) {
      _automaticRetry?.cancel();
      _automaticRetry = null;
      _attempt = 0;
    }
  }

  @override
  void dispose() {
    _automaticRetry?.cancel();
    super.dispose();
  }

  void _retry() {
    _automaticRetry?.cancel();
    _automaticRetry = null;
    setState(() => _attempt++);
  }

  void _retryOnceAfterFailure() {
    if (_attempt != 0 || _automaticRetry != null) return;
    _automaticRetry = Timer(const Duration(seconds: 2), () {
      if (mounted) _retry();
    });
  }

  Widget _fallback() {
    final local = widget.localFallback;
    if (local != null) {
      return Image.file(
        local,
        width: widget.width,
        height: widget.height,
        fit: widget.fit,
        errorBuilder: (_, __, ___) => _emptyImage(),
      );
    }
    return _emptyImage();
  }

  Widget _emptyImage() => const ColoredBox(
        color: AppTheme.cardBeige,
        child: Center(
          child:
              Icon(Icons.image_outlined, size: 32, color: AppTheme.textMuted),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final base = EnvironmentConfig.apiBaseUrl;
    final uri = widget.path.startsWith('http')
        ? widget.path
        : '$base${widget.path.startsWith('/') ? '' : '/'}${widget.path}';
    final retryUri = _attempt == 0
        ? uri
        : '$uri${uri.contains('?') ? '&' : '?'}retry=$_attempt';

    return SizedBox(
      width: widget.width,
      height: widget.height,
      child: Image.network(
        retryUri,
        width: widget.width,
        height: widget.height,
        fit: widget.fit,
        gaplessPlayback: true,
        loadingBuilder: (context, image, progress) {
          if (progress == null) return image;
          return Stack(
            fit: StackFit.expand,
            children: <Widget>[
              _fallback(),
              Positioned(
                right: 12,
                bottom: 12,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppTheme.moss.withValues(alpha: 0.88),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    child: Text('Đang tải ảnh phân tích',
                        style: TextStyle(color: Colors.white, fontSize: 12)),
                  ),
                ),
              ),
            ],
          );
        },
        errorBuilder: (context, error, stackTrace) {
          _retryOnceAfterFailure();
          return Stack(
            fit: StackFit.expand,
            children: <Widget>[
              _fallback(),
              Positioned(
                left: 10,
                right: 10,
                bottom: 10,
                child: Center(
                  child: FilledButton.tonalIcon(
                    onPressed: _retry,
                    icon: const Icon(Icons.refresh_rounded, size: 18),
                    label: const Text('Tải lại ảnh phân tích'),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
