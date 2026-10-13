import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'core/config/environment_config.dart';
import 'firebase_options.dart';
import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await EnvironmentConfig.load();
  try {
    await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform);
  } catch (e) {
    debugPrint("Firebase chưa cấu hình: $e");
  }
  runApp(const RiceAiApp());
}
