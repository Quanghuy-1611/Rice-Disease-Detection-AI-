import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as image;
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/services/prediction_service.dart';
import 'package:mobile_app/views/screens/plus_screen.dart';

class _FakePredictionService extends PredictionService {
  _FakePredictionService({this.exhausted = false});

  final bool exhausted;

  static const plan = <String, dynamic>{
    'plan': 'plus',
    'unlimited': true,
    'remaining': null,
    'limits': <String, int>{'basic': 15, 'plus': 80},
  };

  @override
  Future<Map<String, dynamic>> getPlan() async => exhausted
      ? <String, dynamic>{...plan, 'unlimited': false, 'remaining': 0}
      : plan;

  @override
  Future<Map<String, dynamic>> predictPlus(List<File> images) async =>
      <String, dynamic>{
        'prediction': null,
        'message': 'Các ảnh chưa thống nhất hoặc chưa đủ rõ.',
        'images': <Map<String, dynamic>>[
          for (final _ in images)
            <String, dynamic>{'prediction': null, 'disagreement': true},
        ],
        'plan': plan,
      };
}

void main() {
  testWidgets('Plus selects, removes and reports uncertain images',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final directory = Directory.systemTemp.createTempSync('riceai-plus-ui-');
    addTearDown(() => directory.deleteSync(recursive: true));
    final photo = image.Image(width: 12, height: 12);
    final first = File('${directory.path}/first.png')
      ..writeAsBytesSync(image.encodePng(photo));
    final second = File('${directory.path}/second.png')
      ..writeAsBytesSync(image.encodePng(photo));

    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(useMaterial3: true),
      home: PlusScreen(
        service: _FakePredictionService(),
        openGalleryOnStart: true,
        selectImages: () async =>
            <XFile>[XFile(first.path), XFile(second.path)],
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('2/5 ảnh'), findsOneWidget);
    expect(find.text('Phân tích 2 ảnh'), findsOneWidget);
    await tester.tap(find.byTooltip('Bỏ ảnh 1'));
    await tester.pumpAndSettle();
    expect(find.text('1/5 ảnh'), findsOneWidget);

    await tester.tap(find.text('Phân tích 1 ảnh'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Chưa thể kết luận chung'),
      180,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Chưa thể kết luận chung'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Hai mô hình chưa thống nhất ở ảnh này.'),
      180,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Hai mô hình chưa thống nhất ở ảnh này.'), findsOneWidget);
  });

  testWidgets('Plus stops at five photos and respects exhausted quota',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    final directory = Directory.systemTemp.createTempSync('riceai-plus-limit-');
    addTearDown(() => directory.deleteSync(recursive: true));
    final photo = File('${directory.path}/photo.png')
      ..writeAsBytesSync(image.encodePng(image.Image(width: 12, height: 12)));
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(useMaterial3: true),
      home: PlusScreen(
        service: _FakePredictionService(exhausted: true),
        openGalleryOnStart: true,
        selectImages: () async =>
            List<XFile>.generate(5, (_) => XFile(photo.path)),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('5/5 ảnh'), findsOneWidget);
    expect(find.text('Còn 0/80 lượt tháng này'), findsOneWidget);
    final submit = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Đã hết lượt Plus'));
    expect(submit.onPressed, isNull);
    final camera = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, 'Chụp ảnh'));
    expect(camera.onPressed, isNull);
  });
}
