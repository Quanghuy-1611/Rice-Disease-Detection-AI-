/// Model dữ liệu cho bệnh lúa
class DiseaseInfo {
  const DiseaseInfo({
    required this.id,
    required this.name,
    required this.nameEn,
    required this.shortDesc,
    required this.symptoms,
    required this.conditions,
    required this.prevention,
    required this.treatment,
    required this.category,
    this.severityApplicable = true,
  });

  final String id;
  final String name;
  final String nameEn;
  final String shortDesc;
  final String symptoms;
  final String conditions;
  final String prevention;
  final String treatment;
  final DiseaseCategory category;

  /// Chỉ hiện severity cho bệnh lá; sâu/ốc/cỏ = false
  final bool severityApplicable;
}

enum DiseaseCategory { leafDisease, pestInsect, weed, healthy, other }

extension DiseaseCategoryLabel on DiseaseCategory {
  String get label => switch (this) {
        DiseaseCategory.leafDisease => 'Bệnh lá',
        DiseaseCategory.pestInsect => 'Sâu / ốc',
        DiseaseCategory.weed => 'Cỏ dại',
        DiseaseCategory.healthy => 'Khỏe mạnh',
        DiseaseCategory.other => 'Khác',
      };
}

/// Model một lần quét lịch sử
class HistoryItem {
  const HistoryItem({
    required this.id,
    required this.diseaseName,
    required this.date,
    required this.confidence,
    this.note,
    this.location,
    this.category = DiseaseCategory.leafDisease,
  });

  final String id;
  final String diseaseName;
  final DateTime date;
  final double confidence;
  final String? note;
  final String? location;
  final DiseaseCategory category;
}
