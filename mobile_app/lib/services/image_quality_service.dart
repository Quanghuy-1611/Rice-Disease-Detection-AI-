import 'dart:io';
import 'dart:math' as math;

import 'package:image/image.dart' as img;

enum ImageQualityIssue { blurry, tooDark, overexposed }

class ImageQualityResult {
  const ImageQualityResult({
    required this.issue,
    required this.luminance,
    required this.laplacianVariance,
  });

  final ImageQualityIssue? issue;
  final double luminance;
  final double laplacianVariance;

  bool get isAcceptable => issue == null;

  String get message => switch (issue) {
        ImageQualityIssue.blurry => 'Ảnh bị mờ, hãy giữ máy chắc hơn.',
        ImageQualityIssue.tooDark => 'Ảnh quá tối, hãy chụp nơi đủ sáng hơn.',
        ImageQualityIssue.overexposed => 'Ảnh bị chói, hãy đổi góc chụp.',
        null => '',
      };
}

class ImageQualityService {
  // Conservative client-side thresholds. They only warn; the farmer may still
  // continue because an unusual lighting condition is not a diagnosis error.
  static const double _minLuminance = 42;
  static const double _maxLuminance = 220;
  static const double _minLaplacianVariance = 55;
  static const int _maxCheckSide = 512;

  Future<ImageQualityResult> checkQuality(File imageFile) async {
    final bytes = await imageFile.readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      throw const FormatException('Không đọc được nội dung ảnh.');
    }
    final source = img.bakeOrientation(decoded);
    final scale = math.min(
      1.0,
      _maxCheckSide / math.max(source.width, source.height),
    );
    final image = scale < 1
        ? img.copyResize(
            source,
            width: (source.width * scale).round(),
            height: (source.height * scale).round(),
          )
        : source;
    final luminance = _meanLuminance(image);
    final variance = _laplacianVariance(image);
    final issue = luminance < _minLuminance
        ? ImageQualityIssue.tooDark
        : luminance > _maxLuminance
            ? ImageQualityIssue.overexposed
            : variance < _minLaplacianVariance
                ? ImageQualityIssue.blurry
                : null;
    return ImageQualityResult(
      issue: issue,
      luminance: luminance,
      laplacianVariance: variance,
    );
  }

  double _gray(img.Image image, int x, int y) {
    final pixel = image.getPixel(x, y);
    return 0.299 * pixel.r.toDouble() +
        0.587 * pixel.g.toDouble() +
        0.114 * pixel.b.toDouble();
  }

  double _meanLuminance(img.Image image) {
    var sum = 0.0;
    for (var y = 0; y < image.height; y += 2) {
      for (var x = 0; x < image.width; x += 2) {
        sum += _gray(image, x, y);
      }
    }
    final samples = ((image.width + 1) ~/ 2) * ((image.height + 1) ~/ 2);
    return sum / samples;
  }

  double _laplacianVariance(img.Image image) {
    if (image.width < 3 || image.height < 3) return 0;
    var sum = 0.0;
    var sumSquares = 0.0;
    var count = 0;
    for (var y = 1; y < image.height - 1; y += 2) {
      for (var x = 1; x < image.width - 1; x += 2) {
        final laplacian =
            _gray(image, x - 1, y) +
            _gray(image, x + 1, y) +
            _gray(image, x, y - 1) +
            _gray(image, x, y + 1) -
            4 * _gray(image, x, y);
        sum += laplacian;
        sumSquares += laplacian * laplacian;
        count++;
      }
    }
    if (count == 0) return 0;
    final mean = sum / count;
    return math.max(0, sumSquares / count - mean * mean);
  }
}
