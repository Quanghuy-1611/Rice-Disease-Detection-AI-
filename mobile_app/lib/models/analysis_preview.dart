enum AnalysisPreview {
  original,
  aiHeatmap,
  leafMask,
  agriCam,
}

extension AnalysisPreviewCopy on AnalysisPreview {
  String get title => switch (this) {
        AnalysisPreview.original => 'Ảnh gốc',
        AnalysisPreview.aiHeatmap => 'H_AI',
        AnalysisPreview.leafMask => 'M_veg',
        AnalysisPreview.agriCam => 'Agri-CAM',
      };

  String get caption => switch (this) {
        AnalysisPreview.original => 'Ảnh lá lúa vừa chụp ngoài đồng',
        AnalysisPreview.aiHeatmap => 'Vùng AI dùng để dự đoán bệnh',
        AnalysisPreview.leafMask => 'Vùng lá được giữ lại để phân tích',
        AnalysisPreview.agriCam => 'Attention sau khi loại activation nền',
      };
}
