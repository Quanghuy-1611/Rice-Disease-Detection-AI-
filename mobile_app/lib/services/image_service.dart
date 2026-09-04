import 'dart:io';

import 'package:image_picker/image_picker.dart';

class ImageService {
  final ImagePicker _picker = ImagePicker();

  /// Pick an image from the gallery.
  Future<File?> pickFromGallery() async {
    try {
      final XFile? xFile = await _picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 80, // Compress slightly to save bandwidth
      );
      if (xFile != null) {
        return File(xFile.path);
      }
    } catch (e) {
      // Handle or log error
    }
    return null;
  }

}
