import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/theme/app_theme.dart';
import '../../services/image_service.dart';
import 'analysis_screen.dart';

class CameraScreen extends StatefulWidget {
  final String analysisMode;

  const CameraScreen({
    super.key,
    this.analysisMode = 'basic',
  });

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen>
    with SingleTickerProviderStateMixin {
  bool _flashOn = false;
  late final AnimationController _scanAnim;
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  final ImageService _imageService = ImageService();

  @override
  void initState() {
    super.initState();
    _scanAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);
    _initCamera();
  }

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        final backCamera = _cameras!.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.back,
          orElse: () => _cameras!.first,
        );
        _controller = CameraController(
          backCamera,
          ResolutionPreset.high,
          enableAudio: false,
        );
        await _controller!.initialize();
        if (mounted) setState(() {});
      }
    } catch (e) {
      debugPrint('Camera error: $e');
    }
  }

  @override
  void dispose() {
    _scanAnim.dispose();
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _takePicture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    try {
      final XFile file = await _controller!.takePicture();
      final File imgFile = File(file.path);
      _goToAnalysis(imgFile);
    } catch (e) {
      debugPrint('Error taking picture: $e');
    }
  }

  Future<void> _pickGallery() async {
    final File? file = await _imageService.pickFromGallery();
    if (file != null) {
      _goToAnalysis(file);
    }
  }

  Future<void> _switchCamera() async {
    if (_cameras == null || _cameras!.length < 2) return;
    final lensDirection = _controller!.description.lensDirection;
    CameraDescription newDescription = _cameras!.firstWhere(
        (cam) => cam.lensDirection != lensDirection,
        orElse: () => _cameras![0]);

    await _controller?.dispose();
    _controller = CameraController(
      newDescription,
      ResolutionPreset.high,
      enableAudio: false,
    );
    try {
      await _controller!.initialize();
      if (mounted) setState(() {});
    } catch (e) {
      debugPrint('Error switching camera: $e');
    }
  }

  void _goToAnalysis(File imageFile) {
    Navigator.of(context).pushReplacement(
      PageRouteBuilder<void>(
        pageBuilder: (_, __, ___) => AnalysisScreen(
          imageFile: imageFile,
          analysisMode: widget.analysisMode,
        ),
        transitionsBuilder: (_, animation, __, child) =>
            FadeTransition(opacity: animation, child: child),
        transitionDuration: const Duration(milliseconds: 350),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final double screenH = MediaQuery.of(context).size.height;
    final double screenW = MediaQuery.of(context).size.width;
    final double frameSize = screenW * 0.72;

    return Scaffold(
      backgroundColor: const Color(0xFF0A1A0F),
      body: Stack(
        children: <Widget>[
          // ── Camera Preview ──────────────────
          SizedBox.expand(
            child: _controller != null && _controller!.value.isInitialized
                ? CameraPreview(_controller!)
                : CustomPaint(painter: _CamBgPainter()),
          ),

          // ── Live-camera hint ──────────────────────
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 0,
            right: 0,
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.warningOrange.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(100),
                ),
                child: const Text(
                  '📷  Camera trực tiếp',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ).animate().fade(duration: 400.ms).slideY(begin: -0.3),
            ),
          ),

          // ── Nút đóng ─────────────────────────────
          Positioned(
            top: MediaQuery.of(context).padding.top + 10,
            left: 16,
            child: Material(
              color: Colors.white.withValues(alpha: 0.12),
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: () => Navigator.of(context).pop(),
                child: const Padding(
                  padding: EdgeInsets.all(10),
                  child:
                      Icon(Icons.close_rounded, color: Colors.white, size: 22),
                ),
              ),
            ),
          ),

          // ── Flash toggle ─────────────────────────
          Positioned(
            top: MediaQuery.of(context).padding.top + 10,
            right: 16,
            child: Material(
              color: _flashOn
                  ? AppTheme.neonLeaf.withValues(alpha: 0.85)
                  : Colors.white.withValues(alpha: 0.12),
              shape: const CircleBorder(),
              child: InkWell(
                customBorder: const CircleBorder(),
                onTap: () async {
                  if (_controller != null) {
                    final newFlashMode =
                        _flashOn ? FlashMode.off : FlashMode.torch;
                    await _controller!.setFlashMode(newFlashMode);
                    setState(() => _flashOn = !_flashOn);
                  }
                },
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: Icon(
                    _flashOn ? Icons.flash_on_rounded : Icons.flash_off_rounded,
                    color: _flashOn ? AppTheme.moss : Colors.white,
                    size: 22,
                  ),
                ),
              ),
            ),
          ),

          // ── Scan frame ────────────────────────────
          Center(
            child: SizedBox(
              width: frameSize,
              height: frameSize,
              child: Stack(
                children: <Widget>[
                  // Corner brackets
                  ..._buildCorners(frameSize),

                  // Animated scan line
                  AnimatedBuilder(
                    animation: _scanAnim,
                    builder: (_, __) {
                      return Positioned(
                        left: 0,
                        right: 0,
                        top: (frameSize - 4) * _scanAnim.value,
                        child: Container(
                          height: 3,
                          margin: const EdgeInsets.symmetric(horizontal: 8),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: <Color>[
                                Colors.transparent,
                                AppTheme.neonLeaf,
                                Colors.transparent,
                              ],
                            ),
                            borderRadius: BorderRadius.circular(2),
                            boxShadow: <BoxShadow>[
                              BoxShadow(
                                color: AppTheme.neonLeaf.withValues(alpha: 0.6),
                                blurRadius: 10,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            )
                .animate()
                .fade(delay: 200.ms)
                .scale(begin: const Offset(0.9, 0.9)),
          ),

          // ── Tip text ────────────────────────────
          Center(
            child: Padding(
              padding: EdgeInsets.only(top: frameSize * 0.56 + screenH * 0.02),
              child: const Text(
                'Căn lá lúa vào khung\nchụp cận cảnh, đủ sáng',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  height: 1.5,
                ),
              ).animate(delay: 300.ms).fade(),
            ),
          ),

          // ── Bottom controls ───────────────────────
          Positioned(
            bottom: MediaQuery.of(context).padding.bottom + 36,
            left: 0,
            right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: <Widget>[
                // Gallery button
                _ControlButton(
                  icon: Icons.photo_library_outlined,
                  label: 'Thư viện',
                  onTap: _pickGallery,
                ).animate(delay: 150.ms).fade().slideY(begin: 0.3),

                // Shutter button
                _ShutterButton(onTap: _takePicture)
                    .animate(delay: 100.ms)
                    .fade()
                    .scale(begin: const Offset(0.8, 0.8)),

                // Flip camera button
                _ControlButton(
                  icon: Icons.flip_camera_ios_outlined,
                  label: 'Đổi máy',
                  onTap: _switchCamera,
                ).animate(delay: 150.ms).fade().slideY(begin: 0.3),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildCorners(double size) {
    const double len = 26;
    const double thick = 3.0;
    const Color color = AppTheme.neonLeaf;
    const double r = 6;

    Widget corner({
      required double top,
      required double left,
      required double right,
      required double bottom,
    }) {
      return Positioned(
        top: top == -1 ? null : top,
        left: left == -1 ? null : left,
        right: right == -1 ? null : right,
        bottom: bottom == -1 ? null : bottom,
        child: SizedBox(
          width: len,
          height: len,
          child: CustomPaint(
            painter: _CornerPainter(
              fromTop: top != -1,
              fromLeft: left != -1,
              color: color,
              thick: thick,
              radius: r,
            ),
          ),
        ),
      );
    }

    return <Widget>[
      corner(top: 0, left: 0, right: -1, bottom: -1),
      corner(top: 0, left: -1, right: 0, bottom: -1),
      corner(top: -1, left: 0, right: -1, bottom: 0),
      corner(top: -1, left: -1, right: 0, bottom: 0),
    ];
  }
}

class _ShutterButton extends StatelessWidget {
  const _ShutterButton({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 76,
        height: 76,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3.5),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: AppTheme.neonLeaf.withValues(alpha: 0.35),
              blurRadius: 20,
              spreadRadius: 4,
            ),
          ],
        ),
        child: Center(
          child: Container(
            width: 60,
            height: 60,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white,
            ),
          ),
        ),
      ),
    );
  }
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: Colors.white, size: 24),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Custom Painters ──────────────────────────────

class _CamBgPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    // Dark gradient background simulating camera
    final Paint bg = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[Color(0xFF0A1A0F), Color(0xFF122010)],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, bg);

    // Subtle field pattern
    final Paint grid = Paint()
      ..color = const Color(0xFF1E3A25)
      ..strokeWidth = 0.5;
    for (double x = 0; x < size.width; x += 40) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (double y = 0; y < size.height; y += 40) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _CornerPainter extends CustomPainter {
  const _CornerPainter({
    required this.fromTop,
    required this.fromLeft,
    required this.color,
    required this.thick,
    required this.radius,
  });

  final bool fromTop;
  final bool fromLeft;
  final Color color;
  final double thick;
  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..strokeWidth = thick
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final double w = size.width;
    final double h = size.height;

    if (fromTop && fromLeft) {
      canvas.drawLine(Offset(radius, 0), Offset(w, 0), paint);
      canvas.drawLine(Offset(0, radius), Offset(0, h), paint);
      canvas.drawArc(Rect.fromLTWH(0, 0, radius * 2, radius * 2), 3.14159,
          3.14159 / 2, false, paint);
    } else if (fromTop && !fromLeft) {
      canvas.drawLine(Offset(0, 0), Offset(w - radius, 0), paint);
      canvas.drawLine(Offset(w, radius), Offset(w, h), paint);
      canvas.drawArc(Rect.fromLTWH(w - radius * 2, 0, radius * 2, radius * 2),
          -3.14159 / 2, 3.14159 / 2, false, paint);
    } else if (!fromTop && fromLeft) {
      canvas.drawLine(Offset(radius, h), Offset(w, h), paint);
      canvas.drawLine(Offset(0, 0), Offset(0, h - radius), paint);
      canvas.drawArc(Rect.fromLTWH(0, h - radius * 2, radius * 2, radius * 2),
          3.14159 / 2, 3.14159 / 2, false, paint);
    } else {
      canvas.drawLine(Offset(0, h), Offset(w - radius, h), paint);
      canvas.drawLine(Offset(w, 0), Offset(w, h - radius), paint);
      canvas.drawArc(
          Rect.fromLTWH(w - radius * 2, h - radius * 2, radius * 2, radius * 2),
          0,
          3.14159 / 2,
          false,
          paint);
    }
  }

  @override
  bool shouldRepaint(covariant _CornerPainter oldDelegate) => false;
}
