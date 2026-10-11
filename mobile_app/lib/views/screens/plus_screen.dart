import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/config/environment_config.dart';
import '../../core/config/seven_class_catalog.dart';
import '../../core/errors/api_exception.dart';
import '../../core/theme/app_theme.dart';
import '../../services/prediction_service.dart';

class PlusScreen extends StatefulWidget {
  const PlusScreen({super.key});

  @override
  State<PlusScreen> createState() => _PlusScreenState();
}

class _PlusScreenState extends State<PlusScreen> {
  final _picker = ImagePicker();
  final _service = PredictionService();
  List<File> _images = <File>[];
  Map<String, dynamic>? _result;
  Map<String, dynamic>? _plan;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadPlan();
  }

  Future<void> _loadPlan() async {
    try {
      final plan = await _service.getPlan();
      if (mounted) setState(() => _plan = plan);
    } catch (_) {
      // The prediction call still reports the authoritative quota.
    }
  }

  Future<void> _pickImages() async {
    final selected =
        await _picker.pickMultiImage(imageQuality: 80, maxWidth: 1600);
    if (!mounted || selected.isEmpty) return;
    if (selected.length > 5) {
      setState(() => _error = 'Chọn tối đa 5 ảnh trong mỗi lượt.');
      return;
    }
    setState(() {
      _images = selected.map((file) => File(file.path)).toList();
      _result = null;
      _error = null;
    });
  }

  Future<void> _takePhoto() async {
    if (_images.length >= 5) {
      setState(() => _error = 'Đã đủ 5 ảnh cho lượt này.');
      return;
    }
    final photo = await _picker.pickImage(
        source: ImageSource.camera, imageQuality: 80, maxWidth: 1600);
    if (!mounted || photo == null) return;
    setState(() {
      _images = <File>[..._images, File(photo.path)];
      _result = null;
      _error = null;
    });
  }

  Future<void> _analyze() async {
    if (_images.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await _service.predictPlus(_images);
      if (!mounted) return;
      setState(() {
        _result = result;
        if (result['plan'] is Map) {
          _plan = Map<String, dynamic>.from(result['plan'] as Map);
        }
      });
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
            () => _error = 'Chưa phân tích được bộ ảnh. Vui lòng thử lại.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    final items = result?['images'] is List
        ? List<Map<String, dynamic>>.from((result!['images'] as List)
            .map((item) => Map<String, dynamic>.from(item as Map)))
        : <Map<String, dynamic>>[];
    final quota = _plan;
    final advice = result?['ipm_advice'] is Map
        ? Map<String, dynamic>.from(result!['ipm_advice'] as Map)
        : null;
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(title: const Text('RiceAI Plus')),
      body: SafeArea(
          child: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          Text('Phân tích nhiều ảnh',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800, color: AppTheme.textPrimary)),
          const SizedBox(height: 8),
          const Text(
              'Chọn tối đa 5 ảnh của cùng một vấn đề. Khi các ảnh không thống nhất, RiceAI sẽ không kết luận chung.',
              style: TextStyle(color: AppTheme.textSecondary, height: 1.5)),
          if (quota != null) ...<Widget>[
            const SizedBox(height: 16),
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                            quota['unlimited'] == true
                                ? 'Nhân viên · không giới hạn lượt'
                                : 'Còn ${quota['remaining']}/80 lượt trong tháng',
                            style:
                                const TextStyle(fontWeight: FontWeight.w700)),
                        if (quota['halfway_notice'] == true)
                          const Padding(
                              padding: EdgeInsets.only(top: 6),
                              child: Text(
                                  'Bạn đã dùng hơn một nửa số lượt Plus.')),
                      ],
                    ))),
          ],
          const SizedBox(height: 20),
          OutlinedButton.icon(
              onPressed: _busy ? null : _pickImages,
              icon: const Icon(Icons.collections_outlined),
              label: const Text('Chọn ảnh từ thư viện')),
          const SizedBox(height: 8),
          OutlinedButton.icon(
              onPressed: _busy ? null : _takePhoto,
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Chụp thêm ảnh')),
          if (_images.isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            Text('${_images.length} ảnh đã chọn',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _images
                    .map((image) => ClipRRect(
                        borderRadius: BorderRadius.circular(9),
                        child: Image.file(image,
                            width: 95, height: 95, fit: BoxFit.cover)))
                    .toList()),
            const SizedBox(height: 20),
            FilledButton(
                onPressed: _busy ||
                        (quota?['unlimited'] != true &&
                            quota?['remaining'] == 0)
                    ? null
                    : _analyze,
                child: Text(_busy ? 'Đang phân tích...' : 'Phân tích bộ ảnh')),
          ],
          if (_error != null)
            Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text(_error!,
                    style: const TextStyle(color: AppTheme.errorRed))),
          if (result != null) ...<Widget>[
            const SizedBox(height: 25),
            Text(
                result['prediction'] == null
                    ? 'Chưa thể kết luận chung'
                    : SevenClassCatalog.names[result['prediction']] ??
                        'Chưa xác định',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.w800)),
            if (result['message'] != null)
              Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(result['message'].toString())),
            const SizedBox(height: 14),
            ...items.asMap().entries.map((entry) {
              final item = entry.value;
              final url = item['heatmap_url']?.toString() ??
                  '/uploads/${item['filename']}';
              final label = item['prediction']?.toString();
              return Card(
                  child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Image.network('${EnvironmentConfig.apiBaseUrl}$url',
                                width: double.infinity,
                                height: 230,
                                fit: BoxFit.cover),
                            const SizedBox(height: 10),
                            Text(
                                'Ảnh ${entry.key + 1}: ${label == null ? 'Chưa xác định' : SevenClassCatalog.names[label] ?? label}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w800)),
                            if (item['disagreement'] == true)
                              const Text('Hai mô hình không thống nhất.'),
                            if (item['prediction'] != null)
                              Text(
                                  'Mức tự tin: ${((item['confidence'] as num? ?? 0) * 100).toStringAsFixed(1)}%'),
                          ])));
            }),
            if (advice?['recommendation'] is String) ...<Widget>[
              const SizedBox(height: 16),
              Card(
                  child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          const Text('Gợi ý xử lý',
                              style: TextStyle(fontWeight: FontWeight.w800)),
                          const SizedBox(height: 8),
                          Text(advice!['recommendation'].toString()),
                        ],
                      ))),
            ],
            const SizedBox(height: 12),
            const Text(
                'RiceAI chỉ nhận diện các nhóm đã huấn luyện. Hãy đối chiếu với quan sát thực tế trước khi xử lý.',
                style: TextStyle(color: AppTheme.textSecondary)),
          ],
        ],
      )),
    );
  }
}
