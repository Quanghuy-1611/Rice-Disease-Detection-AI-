import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../models/analysis_preview.dart';

class LeafAnalysisPreview extends StatelessWidget {
  const LeafAnalysisPreview({
    super.key,
    required this.preview,
    this.scannerProgress,
  });

  final AnalysisPreview preview;
  final double? scannerProgress;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 4 / 3,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: CustomPaint(
          painter: _LeafAnalysisPainter(
            preview: preview,
            scannerProgress: scannerProgress,
          ),
          child: const SizedBox.expand(),
        ),
      ),
    );
  }
}

class _LeafAnalysisPainter extends CustomPainter {
  const _LeafAnalysisPainter({
    required this.preview,
    required this.scannerProgress,
  });

  final AnalysisPreview preview;
  final double? scannerProgress;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint background = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: <Color>[Color(0xFFE4D9B4), Color(0xFFB7A983)],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, background);

    final Paint shadow = Paint()
      ..color = const Color(0xFF30442D).withOpacity(0.20)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 13);
    canvas.drawOval(
      Rect.fromLTWH(size.width * .14, size.height * .72, size.width * .70,
          size.height * .16),
      shadow,
    );

    final Path leaf = Path()
      ..moveTo(size.width * .14, size.height * .84)
      ..cubicTo(
        size.width * .16,
        size.height * .32,
        size.width * .49,
        size.height * .03,
        size.width * .89,
        size.height * .14,
      )
      ..cubicTo(
        size.width * .82,
        size.height * .55,
        size.width * .50,
        size.height * .87,
        size.width * .14,
        size.height * .84,
      )
      ..close();

    if (preview == AnalysisPreview.leafMask) {
      canvas.drawRect(
        Offset.zero & size,
        Paint()..color = const Color(0xFF14251E),
      );
      canvas.drawPath(leaf, Paint()..color = const Color(0xFF8BD452));
      _drawLeafVeins(canvas, size, color: const Color(0xFF376B31));
      _drawLabel(canvas, size, 'M_veg · Leaf ROI', const Color(0xFFEEFFDF));
      return;
    }

    final Paint leafPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.bottomLeft,
        end: Alignment.topRight,
        colors: <Color>[Color(0xFF2B8D54), Color(0xFF9EDB62)],
      ).createShader(Offset.zero & size);
    canvas.drawPath(leaf, leafPaint);
    _drawLeafVeins(canvas, size, color: const Color(0xFF206B44));
    _drawLesions(canvas, size);

    if (preview == AnalysisPreview.aiHeatmap) {
      _drawHeatSpot(
        canvas,
        Offset(size.width * .48, size.height * .42),
        52,
        opacity: .85,
      );
      _drawHeatSpot(
        canvas,
        Offset(size.width * .71, size.height * .33),
        38,
        opacity: .68,
      );
      _drawHeatSpot(
        canvas,
        Offset(size.width * .12, size.height * .23),
        29,
        opacity: .50,
      );
      _drawLabel(canvas, size, 'H_AI · AI attention', Colors.white);
    }

    if (preview == AnalysisPreview.agriCam) {
      canvas.save();
      canvas.clipPath(leaf);
      _drawHeatSpot(
        canvas,
        Offset(size.width * .48, size.height * .42),
        52,
        opacity: .90,
      );
      _drawHeatSpot(
        canvas,
        Offset(size.width * .71, size.height * .33),
        38,
        opacity: .72,
      );
      canvas.restore();
      _drawLabel(canvas, size, 'Agri-CAM · constrained', Colors.white);
    }

    if (scannerProgress != null) {
      final double y = 12 + (size.height - 24) * scannerProgress!;
      final Paint scanPaint = Paint()
        ..color = AppTheme.neonLeaf.withOpacity(.95)
        ..strokeWidth = 3;
      canvas.drawLine(Offset(12, y), Offset(size.width - 12, y), scanPaint);
      canvas.drawCircle(Offset(size.width * .88, y), 6, scanPaint);
    }
  }

  void _drawLeafVeins(Canvas canvas, Size size, {required Color color}) {
    final Paint vein = Paint()
      ..color = color.withOpacity(.62)
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(
      Offset(size.width * .18, size.height * .79),
      Offset(size.width * .81, size.height * .18),
      vein,
    );
    for (var index = 0; index < 5; index++) {
      final double t = .26 + index * .11;
      final Offset start = Offset(size.width * t, size.height * (1.0 - t));
      canvas.drawLine(
        start,
        Offset(start.dx - size.width * .04, start.dy - size.height * .18),
        vein,
      );
      canvas.drawLine(
        start,
        Offset(start.dx + size.width * .15, start.dy + size.height * .03),
        vein,
      );
    }
  }

  void _drawLesions(Canvas canvas, Size size) {
    final Paint lesion = Paint()
      ..color = const Color(0xFF7B4B28).withOpacity(.72);
    for (final Offset center in <Offset>[
      Offset(size.width * .46, size.height * .42),
      Offset(size.width * .70, size.height * .34),
      Offset(size.width * .60, size.height * .54),
    ]) {
      canvas.drawOval(
        Rect.fromCenter(center: center, width: 20, height: 8),
        lesion,
      );
    }
  }

  void _drawHeatSpot(
    Canvas canvas,
    Offset center,
    double radius, {
    required double opacity,
  }) {
    final Paint spot = Paint()
      ..shader = RadialGradient(
        colors: <Color>[
          const Color(0xFFE53935).withOpacity(opacity),
          const Color(0xFFFFC857).withOpacity(opacity * .68),
          Colors.transparent,
        ],
        stops: const <double>[0, .34, 1],
      ).createShader(Rect.fromCircle(center: center, radius: radius));
    canvas.drawCircle(center, radius, spot);
  }

  void _drawLabel(Canvas canvas, Size size, String label, Color color) {
    final TextPainter painter = TextPainter(
      text: TextSpan(
        text: label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w700,
          letterSpacing: .2,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final Rect badge = Rect.fromLTWH(
      12,
      12,
      painter.width + 20,
      painter.height + 12,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(badge, const Radius.circular(14)),
      Paint()..color = Colors.black.withOpacity(.42),
    );
    painter.paint(canvas, const Offset(22, 18));
  }

  @override
  bool shouldRepaint(covariant _LeafAnalysisPainter oldDelegate) {
    return oldDelegate.preview != preview ||
        oldDelegate.scannerProgress != scannerProgress;
  }
}
