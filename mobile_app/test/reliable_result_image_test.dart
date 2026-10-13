import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mobile_app/core/config/environment_config.dart';
import 'package:mobile_app/views/widgets/reliable_result_image.dart';

void main() {
  late Directory directory;
  late File photo;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'riceai_local_api_base_url': 'http://127.0.0.1:8015',
    });
    await EnvironmentConfig.load();
    directory = await Directory.systemTemp.createTemp('riceai-photo-');
    photo = File('${directory.path}/selected.png');
    await photo.writeAsBytes(img.encodePng(img.Image(width: 2, height: 2)));
  });

  tearDown(() async {
    await directory.delete(recursive: true);
  });

  testWidgets('keeps the selected photo visible when a result download fails',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: ReliableResultImage(
          path: '/uploads/unavailable.jpg',
          localFallback: photo,
          height: 210,
        ),
      ),
    ));
    await tester.pump(const Duration(seconds: 1));

    expect(
      find.byWidgetPredicate(
          (widget) => widget is Image && widget.image is FileImage),
      findsWidgets,
    );
    expect(find.text('Tải lại ảnh phân tích'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
  });
}
