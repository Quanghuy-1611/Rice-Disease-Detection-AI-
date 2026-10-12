import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/config/environment_config.dart';
import '../../core/config/seven_class_catalog.dart';
import '../../core/errors/api_exception.dart';
import '../../core/theme/app_theme.dart';
import '../../services/prediction_service.dart';

class PlusScreen extends StatefulWidget {
  const PlusScreen(
      {super.key,
      this.openCameraOnStart = false,
      this.openGalleryOnStart = false,
      this.service,
      this.selectImages,
      this.capturePhoto});

  final bool openCameraOnStart;
  final bool openGalleryOnStart;
  final PredictionService? service;
  final Future<List<XFile>> Function()? selectImages;
  final Future<XFile?> Function()? capturePhoto;

  @override
  State<PlusScreen> createState() => _PlusScreenState();
}

class _PlusScreenState extends State<PlusScreen> {
  final _picker = ImagePicker();
  late final PredictionService _service;
  List<File> _images = <File>[];
  Map<String, dynamic>? _result;
  Map<String, dynamic>? _plan;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? PredictionService();
    _loadPlan();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.openCameraOnStart) _takePhoto();
      if (widget.openGalleryOnStart) _pickImages();
    });
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
    final selected = await (widget.selectImages?.call() ??
        _picker.pickMultiImage(imageQuality: 80, maxWidth: 1600));
    if (!mounted || selected.isEmpty) return;
    if (_images.length + selected.length > 5) {
      setState(() => _error =
          'Mỗi lượt tối đa 5 ảnh. Bạn còn ${5 - _images.length} chỗ trống.');
      return;
    }
    setState(() {
      _images = <File>[..._images, ...selected.map((file) => File(file.path))];
      _result = null;
      _error = null;
    });
  }

  Future<void> _takePhoto() async {
    if (_images.length >= 5) {
      setState(() => _error = 'Đã đủ 5 ảnh cho lượt này.');
      return;
    }
    final photo = await (widget.capturePhoto?.call() ??
        _picker.pickImage(
            source: ImageSource.camera, imageQuality: 80, maxWidth: 1600));
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
      _result = null;
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

  void _removeImage(int index) {
    setState(() {
      _images = <File>[..._images]..removeAt(index);
      _result = null;
      _error = null;
    });
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
    final unlimited = quota?['unlimited'] == true;
    final remaining = quota?['remaining'] as num?;
    final limit =
        quota?['limits'] is Map ? (quota!['limits'] as Map)['plus'] ?? 80 : 80;
    final canSubmit = _images.isNotEmpty &&
        !_busy &&
        (unlimited || remaining == null || remaining > 0);
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(title: const Text('Chẩn đoán')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: <Widget>[
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.moss,
                borderRadius: BorderRadius.circular(22),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Text('RICEAI PLUS',
                      style: TextStyle(
                          color: AppTheme.neonLeaf,
                          fontWeight: FontWeight.w800,
                          fontSize: 11,
                          letterSpacing: 1)),
                  const SizedBox(height: 8),
                  const Text('Nhìn rõ hơn từ nhiều ảnh',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 21,
                          height: 1.2,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  const Text('Tối đa 5 ảnh trong một lượt chẩn đoán.',
                      style: TextStyle(color: Color(0xFFE2ECE1), height: 1.45)),
                  if (quota != null) ...<Widget>[
                    const SizedBox(height: 12),
                    Text(
                        unlimited
                            ? 'Không giới hạn lượt'
                            : 'Còn ${remaining ?? 0}/$limit lượt tháng này',
                        style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w700)),
                    if (quota['halfway_notice'] == true)
                      const Padding(
                          padding: EdgeInsets.only(top: 6),
                          child: Text('Bạn đã dùng hơn một nửa lượt Plus.',
                              style: TextStyle(color: Color(0xFFE2ECE1)))),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 24),
            Row(children: <Widget>[
              const Expanded(
                  child: Text('Ảnh cần phân tích',
                      style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.textPrimary))),
              Text('${_images.length}/5 ảnh',
                  style: const TextStyle(
                      color: AppTheme.mossMid, fontWeight: FontWeight.w700)),
            ]),
            const SizedBox(height: 5),
            const Text('Chụp gần chỗ có dấu hiệu lạ, đủ sáng và rõ nét.',
                style: TextStyle(color: AppTheme.textSecondary)),
            const SizedBox(height: 15),
            Row(children: <Widget>[
              Expanded(
                  child: OutlinedButton.icon(
                      onPressed:
                          _busy || _images.length == 5 ? null : _takePhoto,
                      icon: const Icon(Icons.camera_alt_outlined, size: 20),
                      label: const Text('Chụp ảnh'),
                      style: OutlinedButton.styleFrom(
                          backgroundColor: AppTheme.cardSolid,
                          minimumSize: const Size.fromHeight(56),
                          padding: const EdgeInsets.symmetric(horizontal: 8)))),
              const SizedBox(width: 9),
              Expanded(
                  child: OutlinedButton.icon(
                      onPressed:
                          _busy || _images.length == 5 ? null : _pickImages,
                      icon: const Icon(Icons.photo_library_outlined, size: 20),
                      label: const Text('Chọn ảnh'),
                      style: OutlinedButton.styleFrom(
                          backgroundColor: AppTheme.cardSolid,
                          minimumSize: const Size.fromHeight(56),
                          padding: const EdgeInsets.symmetric(horizontal: 8)))),
            ]),
            const SizedBox(height: 13),
            if (_images.isEmpty)
              Container(
                height: 115,
                decoration: BoxDecoration(
                    color: AppTheme.cardSolid,
                    borderRadius: BorderRadius.circular(17),
                    border: Border.all(color: AppTheme.borderBeige)),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Icon(Icons.add_photo_alternate_outlined,
                        color: AppTheme.mossMid, size: 27),
                    SizedBox(height: 8),
                    Text('Ảnh bạn chọn sẽ hiện ở đây',
                        style: TextStyle(color: AppTheme.textSecondary)),
                  ],
                ),
              )
            else
              SizedBox(
                height: 106,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: _images.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 9),
                  itemBuilder: (context, index) => Stack(children: <Widget>[
                    ClipRRect(
                        borderRadius: BorderRadius.circular(13),
                        child: Image.file(_images[index],
                            width: 104, height: 104, fit: BoxFit.cover)),
                    Positioned(
                        top: 3,
                        right: 3,
                        child: IconButton.filledTonal(
                          onPressed: _busy ? null : () => _removeImage(index),
                          tooltip: 'Bỏ ảnh ${index + 1}',
                          icon: const Icon(Icons.close_rounded, size: 17),
                          style: IconButton.styleFrom(
                              backgroundColor: AppTheme.cardSolid,
                              minimumSize: const Size(34, 34)),
                        )),
                    Positioned(
                        bottom: 5,
                        left: 6,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 3),
                          decoration: BoxDecoration(
                              color: AppTheme.moss,
                              borderRadius: BorderRadius.circular(6)),
                          child: Text('${index + 1}',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800)),
                        )),
                  ]),
                ),
              ),
            if (_error != null) ...<Widget>[
              const SizedBox(height: 14),
              _Notice(
                  text: _error!,
                  color: AppTheme.errorRed,
                  icon: Icons.error_outline_rounded),
            ],
            if (_busy) ...<Widget>[
              const SizedBox(height: 14),
              const _Notice(
                  text: 'Đang đối chiếu từng ảnh. Bạn giữ ứng dụng mở nhé.',
                  color: AppTheme.moss,
                  icon: Icons.hourglass_top_rounded),
            ],
            if (result != null) ...<Widget>[
              const SizedBox(height: 28),
              const Text('Kết quả phân tích',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary)),
              const SizedBox(height: 12),
              _PlusSummary(result: result),
              const SizedBox(height: 22),
              const Text('Từng ảnh',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary)),
              const SizedBox(height: 12),
              ...items.asMap().entries.map((entry) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _PlusImageResult(
                        index: entry.key + 1, item: entry.value),
                  )),
              if (advice?['recommendation'] is String) ...<Widget>[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                      color: AppTheme.cardBeige,
                      borderRadius: BorderRadius.circular(18)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Text('Gợi ý xử lý',
                          style: TextStyle(
                              fontSize: 17, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 9),
                      Text(advice!['recommendation'].toString(),
                          style: const TextStyle(height: 1.5)),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),
              const Text(
                  'Kết quả chỉ hỗ trợ tham khảo trong các nhóm RiceAI đã học. Hãy kiểm tra cây ngoài ruộng trước khi xử lý.',
                  style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                      height: 1.5)),
            ],
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.fromLTRB(20, 10, 20, 12),
          decoration: const BoxDecoration(
              color: AppTheme.cardSolid,
              border: Border(top: BorderSide(color: AppTheme.borderBeige))),
          child: FilledButton.icon(
            onPressed: canSubmit ? _analyze : null,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.search_rounded),
            label: Text(_busy
                ? 'Đang phân tích'
                : remaining == 0 && !unlimited
                    ? 'Đã hết lượt Plus'
                    : _images.isEmpty
                        ? 'Chọn ảnh để bắt đầu'
                        : 'Phân tích ${_images.length} ảnh'),
            style:
                FilledButton.styleFrom(minimumSize: const Size.fromHeight(54)),
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, required this.color, required this.icon});
  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
            color: color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(13)),
        child: Row(children: <Widget>[
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
              child: Text(text, style: TextStyle(color: color, height: 1.4))),
        ]),
      );
}

class _PlusSummary extends StatelessWidget {
  const _PlusSummary({required this.result});
  final Map<String, dynamic> result;

  @override
  Widget build(BuildContext context) {
    final prediction = result['prediction']?.toString();
    final label = prediction == null
        ? 'Chưa thể kết luận chung'
        : SevenClassCatalog.names[prediction] ?? prediction;
    final message = result['message']?.toString();
    return Container(
      padding: const EdgeInsets.all(19),
      decoration: BoxDecoration(
          color: AppTheme.cardSolid,
          borderRadius: BorderRadius.circular(19),
          border: Border.all(
              color: prediction == null
                  ? AppTheme.warningOrange.withValues(alpha: 0.5)
                  : AppTheme.borderBeige)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(prediction == null ? 'CẦN KIỂM TRA THÊM' : 'KẾT LUẬN CHUNG',
              style: const TextStyle(
                  color: AppTheme.mossMid,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8)),
          const SizedBox(height: 9),
          Text(label,
              style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 24,
                  height: 1.2,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(
              message?.isNotEmpty == true
                  ? message!
                  : prediction == null
                      ? 'Hãy thử ảnh rõ hơn hoặc nhờ người có chuyên môn kiểm tra.'
                      : 'Các ảnh đủ thống nhất để đưa ra kết quả này.',
              style:
                  const TextStyle(color: AppTheme.textSecondary, height: 1.45)),
        ],
      ),
    );
  }
}

class _PlusImageResult extends StatelessWidget {
  const _PlusImageResult({required this.index, required this.item});
  final int index;
  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final prediction = item['prediction']?.toString();
    final label = prediction == null
        ? 'Chưa đủ chắc chắn'
        : SevenClassCatalog.names[prediction] ?? prediction;
    final heatmap = item['heatmap_url']?.toString();
    final filename = item['filename']?.toString();
    final url = heatmap?.isNotEmpty == true
        ? heatmap
        : filename == null
            ? null
            : '/uploads/$filename';
    final confidence = (item['confidence'] as num?)?.toDouble();
    return Container(
      decoration: BoxDecoration(
          color: AppTheme.cardSolid,
          borderRadius: BorderRadius.circular(19),
          border: Border.all(color: AppTheme.borderBeige)),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (url != null)
            Image.network('${EnvironmentConfig.apiBaseUrl}$url',
                width: double.infinity,
                height: 210,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const SizedBox(
                    height: 150,
                    child: Center(child: Text('Chưa tải được ảnh kết quả')))),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('ẢNH $index',
                    style: const TextStyle(
                        color: AppTheme.mossMid,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8)),
                const SizedBox(height: 5),
                Text(label,
                    style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 17,
                        fontWeight: FontWeight.w800)),
                if (prediction == null) ...<Widget>[
                  const SizedBox(height: 5),
                  Text(
                      item['disagreement'] == true
                          ? 'Hai mô hình chưa thống nhất ở ảnh này.'
                          : 'Ảnh này chưa đủ rõ để kết luận.',
                      style: const TextStyle(color: AppTheme.textSecondary)),
                ] else if (confidence != null) ...<Widget>[
                  const SizedBox(height: 5),
                  Text('Mức tự tin: ${(confidence * 100).toStringAsFixed(1)}%',
                      style: const TextStyle(color: AppTheme.textSecondary)),
                ],
                if (heatmap?.isNotEmpty == true) ...<Widget>[
                  const SizedBox(height: 8),
                  const Text('Vùng mô hình chú ý',
                      style: TextStyle(
                          color: AppTheme.textSecondary, fontSize: 12)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
