import 'dart:async';

import 'package:flutter/foundation.dart';

enum DemoScanState { idle, analysing, ready }

class DemoScannerViewModel extends ChangeNotifier {
  static const List<String> stages = <String>[
    'Kiểm tra chất lượng ảnh',
    'Đang gửi ảnh an toàn',
    'Nhận diện bệnh trên lá',
    'Tạo Agri-CAM và severity',
  ];

  DemoScanState _state = DemoScanState.idle;
  int _activeStage = 0;

  DemoScanState get state => _state;
  int get activeStage => _activeStage;
  double get progress =>
      _state == DemoScanState.ready ? 1 : (_activeStage + 1) / stages.length;

  void reset() {
    _state = DemoScanState.idle;
    _activeStage = 0;
    notifyListeners();
  }

  Future<void> runDemo() async {
    _state = DemoScanState.analysing;
    _activeStage = 0;
    notifyListeners();

    for (var index = 0; index < stages.length; index++) {
      _activeStage = index;
      notifyListeners();
      await Future<void>.delayed(const Duration(milliseconds: 760));
    }

    _state = DemoScanState.ready;
    notifyListeners();
  }
}
