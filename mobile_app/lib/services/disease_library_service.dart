import '../core/network/api_client.dart';
import '../core/config/seven_class_catalog.dart';
import '../models/disease_model.dart';

/// Nguồn dữ liệu của Cẩm nang là API FastAPI; không giữ tên bệnh mẫu trên app.
class DiseaseLibraryService {
  final ApiClient _apiClient = ApiClient();

  Future<List<DiseaseInfo>> getDiseases() async {
    final response = await _apiClient.get('/api/disease-library');
    if (response is Map &&
        response['success'] == true &&
        response['data'] is List) {
      final diseases = (response['data'] as List)
          .whereType<Map>()
          .map((item) => _fromApi(Map<String, dynamic>.from(item)))
          .where((disease) => SevenClassCatalog.ids.contains(disease.id))
          .toList();
      diseases.sort((a, b) => SevenClassCatalog.ids
          .indexOf(a.id)
          .compareTo(SevenClassCatalog.ids.indexOf(b.id)));
      return diseases;
    }
    throw Exception('Máy chủ trả về dữ liệu cẩm nang không hợp lệ.');
  }

  DiseaseInfo _fromApi(Map<String, dynamic> item) {
    final category = item['slug'] == 'normal'
        ? DiseaseCategory.healthy
        : switch (item['category']?.toString()) {
            'leaf_disease' => DiseaseCategory.leafDisease,
            'pest' => DiseaseCategory.pestInsect,
            'weed' => DiseaseCategory.weed,
            _ => DiseaseCategory.other,
          };
    String value(String key) => item[key]?.toString().trim() ?? '';
    return DiseaseInfo(
      id: value('slug'),
      name: value('display_name_vi'),
      nameEn: value('display_name_en'),
      shortDesc: value('overview'),
      symptoms: value('symptoms'),
      conditions: value('favorable_conditions'),
      prevention: value('prevention'),
      treatment: value('ipm_advice'),
      category: category,
      severityApplicable: item['severity_applicable'] == true,
    );
  }
}
