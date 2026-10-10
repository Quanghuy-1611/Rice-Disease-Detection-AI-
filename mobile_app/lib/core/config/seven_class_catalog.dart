/// Contract shared with the current seven-class MobileNetV3 Large API and web.
class SevenClassCatalog {
  SevenClassCatalog._();

  static const ids = <String>[
    'bacterial_leaf_blight',
    'brown_spot',
    'golden_apple_snail',
    'leaf_roller',
    'normal',
    'tungro',
    'weeds',
  ];

  static const names = <String, String>{
    'bacterial_leaf_blight': 'Bạc lá vi khuẩn',
    'brown_spot': 'Đốm nâu',
    'golden_apple_snail': 'Ốc bươu vàng',
    'leaf_roller': 'Sâu cuốn lá',
    'normal': 'Lúa khỏe mạnh',
    'tungro': 'Vàng lùn Tungro',
    'weeds': 'Cỏ dại',
  };
}
