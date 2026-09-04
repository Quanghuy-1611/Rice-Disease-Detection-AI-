import 'dart:io';

import 'package:image/image.dart' as img;
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';

class ImageProcessingResult {
  const ImageProcessingResult({
    required this.file,
    required this.originalBytes,
    required this.processedBytes,
  });

  final File file;
  final int originalBytes;
  final int processedBytes;
}

class ImageProcessingService {
  static const _maxSide = 1024;
  static const _jpegQuality = 85;

  Future<ImageProcessingResult> processImage(File imageFile) async {
    final original = await imageFile.readAsBytes();
    final decoded = img.decodeImage(original);
    if (decoded == null) {
      throw const FormatException('Không thể nén ảnh vì dữ liệu ảnh không hợp lệ.');
    }
    var processed = img.bakeOrientation(decoded);
    final longestSide = processed.width > processed.height
        ? processed.width
        : processed.height;
    if (longestSide > _maxSide) {
      processed = processed.width >= processed.height
          ? img.copyResize(processed, width: _maxSide)
          : img.copyResize(processed, height: _maxSide);
    }
    final output = img.encodeJpg(processed, quality: _jpegQuality);
    final temporaryDirectory = await getTemporaryDirectory();
    final outputFile = File(
      path.join(
        temporaryDirectory.path,
        'riceai_${DateTime.now().microsecondsSinceEpoch}.jpg',
      ),
    );
    await outputFile.writeAsBytes(output, flush: true);
    // Helpful when profiling bandwidth; avoid showing noisy bytes in normal UI.
    // ignore: avoid_print
    print('RiceAI upload image: ${original.length}B -> ${output.length}B');
    return ImageProcessingResult(
      file: outputFile,
      originalBytes: original.length,
      processedBytes: output.length,
    );
  }
}
