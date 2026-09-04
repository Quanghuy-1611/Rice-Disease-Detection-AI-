import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/config/environment_config.dart';
import '../../core/theme/app_theme.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({
    super.key,
    required this.predictionData,
    required this.imageFile,
  });

  final Map<String, dynamic> predictionData;
  final File imageFile;

  Map<String, dynamic> get _agriCam {
    final raw = predictionData['agri_cam'];
    return raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
  }

  bool get _isPlus =>
      predictionData['analysis_mode'] == 'plus' && _agriCam.isNotEmpty;

  List<_ResultTab> get _tabs {
    final tabs = <_ResultTab>[
      const _ResultTab(
        title: 'Ảnh gốc',
        caption: 'Ảnh lá lúa vừa được gửi để phân tích.',
      ),
    ];
    final basic = predictionData['heatmap_url']?.toString();
    if (basic != null && basic.isNotEmpty) {
      tabs.add(const _ResultTab(
        title: 'Grad-CAM',
        caption: 'Vùng mô hình phân loại sử dụng để đưa ra dự đoán.',
        urlKey: 'heatmap_url',
      ));
    }
    if (_isPlus) {
      if (_agriCam['ai_heatmap_url'] != null) {
        tabs.add(const _ResultTab(
          title: 'H_AI',
          caption: 'Bản đồ Grad-CAM++ đa tầng trước khi áp ràng buộc vùng lá.',
          urlKey: 'ai_heatmap_url',
        ));
      }
      if (_agriCam['leaf_mask_url'] != null) {
        tabs.add(const _ResultTab(
          title: 'Mask lá',
          caption: 'Vùng lá được giữ lại từ mô xanh, vàng úa và mô hoại tử.',
          urlKey: 'leaf_mask_url',
        ));
      }
      if (_agriCam['hybrid_heatmap_url'] != null) {
        tabs.add(const _ResultTab(
          title: 'Agri-CAM',
          caption: 'Vùng AI quan tâm sau khi được ràng buộc theo vùng lá.',
          urlKey: 'hybrid_heatmap_url',
        ));
      }
    }
    return tabs;
  }

  String? _urlFor(_ResultTab tab) {
    if (tab.urlKey == null) return null;
    if (tab.urlKey == 'heatmap_url') {
      return predictionData['heatmap_url']?.toString();
    }
    return _agriCam[tab.urlKey]?.toString();
  }

  @override
  Widget build(BuildContext context) {
    final tabs = _tabs;
    return DefaultTabController(
      length: tabs.length,
      child: Scaffold(
        backgroundColor: AppTheme.porcelain,
        appBar: AppBar(
          leading: IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.arrow_back_rounded),
            tooltip: 'Quay lại',
          ),
          title: const Text(
            'Báo cáo chẩn đoán',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
        ),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
            children: <Widget>[
              _MedicalReportHeader(
                predictionData: predictionData,
                agriCam: _agriCam,
                isPlus: _isPlus,
              ).animate().fade().slideY(begin: 0.08, end: 0),
              const SizedBox(height: 22),
              if (tabs.length > 1) ...<Widget>[
                Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    color: AppTheme.moss.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: TabBar(
                    isScrollable: true,
                    tabAlignment: TabAlignment.start,
                    dividerColor: Colors.transparent,
                    indicatorSize: TabBarIndicatorSize.tab,
                    indicator: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(100),
                    ),
                    labelColor: AppTheme.moss,
                    unselectedLabelColor: AppTheme.textSecondary,
                    labelStyle: const TextStyle(
                        fontWeight: FontWeight.w800, fontSize: 12),
                    unselectedLabelStyle: const TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 12),
                    tabs: tabs.map((tab) => Tab(text: tab.title)).toList(),
                  ),
                ),
                const SizedBox(height: 14),
              ],
              SizedBox(
                height: 340,
                child: TabBarView(
                  physics: tabs.length == 1
                      ? const NeverScrollableScrollPhysics()
                      : null,
                  children: tabs.map((tab) {
                    return _ImageExplanation(
                      imageFile: imageFile,
                      url: _urlFor(tab),
                      caption: tab.caption,
                    );
                  }).toList(),
                ),
              ).animate().fade(delay: 160.ms),
              const SizedBox(height: 22),
              _IPMCard(
                ipmAdvice: predictionData['ipm_advice']?.toString() ??
                    'Chưa có thông tin khuyến nghị.',
              ).animate().fade(delay: 240.ms),
              const SizedBox(height: 26),
              FilledButton.icon(
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.camera_alt_rounded, size: 20),
                label: const Text('Quét ảnh khác'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(54),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ResultTab {
  const _ResultTab({
    required this.title,
    required this.caption,
    this.urlKey,
  });

  final String title;
  final String caption;
  final String? urlKey;
}

class _MedicalReportHeader extends StatelessWidget {
  const _MedicalReportHeader({
    required this.predictionData,
    required this.agriCam,
    required this.isPlus,
  });

  final Map<String, dynamic> predictionData;
  final Map<String, dynamic> agriCam;
  final bool isPlus;

  static const Map<String, String> _vietnameseNames = <String, String>{
    'bacterial_leaf_blight': 'Bạc lá vi khuẩn',
    'bacterial_leaf_streak': 'Sọc lá vi khuẩn',
    'bacterial_panicle_blight': 'Bạc bông vi khuẩn',
    'beetle': 'Bọ cánh cứng hại lúa',
    'blast': 'Đạo ôn',
    'brown_planthopper': 'Rầy nâu',
    'brown_spot': 'Đốm nâu',
    'dead_heart': 'Dảnh héo',
    'downy_mildew': 'Sương mai',
    'golden_apple_snail': 'Ốc bươu vàng',
    'leaf_roller': 'Sâu cuốn lá',
    'leaf_smut': 'Lem lép hạt / than lá',
    'normal': 'Lúa khỏe mạnh',
    'sheath_blight': 'Khô vằn',
    'southern_black_streaked_dwarf': 'Lùn sọc đen phương nam',
    'stem_borer': 'Sâu đục thân',
    'tungro': 'Vàng lùn Tungro',
    'weeds': 'Cỏ dại',
    'whitebacked_planthopper': 'Rầy lưng trắng',
  };

  @override
  Widget build(BuildContext context) {
    final classId = predictionData['prediction']?.toString() ?? 'unknown';
    final confidence = (predictionData['confidence'] as num?)?.toDouble() ?? 0;
    final confidenceText = '${(confidence * 100).toStringAsFixed(1)}%';
    final normal = classId == 'normal';
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: AppTheme.cardSolid,
        borderRadius: BorderRadius.circular(24),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppTheme.moss.withValues(alpha: 0.07),
            blurRadius: 22,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              _StatusChip(
                label: normal ? 'BÌNH THƯỜNG' : 'PHÁT HIỆN',
                color: normal ? AppTheme.safeGreen : AppTheme.warningOrange,
              ),
              const SizedBox(width: 8),
              _StatusChip(
                label: isPlus ? 'PLUS · AGRI-CAM' : 'BASIC · GRAD-CAM',
                color: AppTheme.moss,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            _vietnameseNames[classId] ?? classId,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: AppTheme.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
          ),
          const SizedBox(height: 5),
          Text(
            '$classId · ${predictionData['model_family'] ?? 'MobileNetV3Large'}',
            style: const TextStyle(
              color: AppTheme.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 20),
          const Divider(height: 1),
          const SizedBox(height: 16),
          _MetricRow(label: 'Độ tin cậy phân loại', value: confidenceText),
          const SizedBox(height: 14),
          _SeverityStatus(agriCam: agriCam, isPlus: isPlus),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(100),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 10,
            letterSpacing: 0.5,
            fontWeight: FontWeight.w900,
          ),
        ),
      );
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Text(label,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontWeight: FontWeight.w600)),
          Text(value,
              style: const TextStyle(
                  color: AppTheme.moss, fontWeight: FontWeight.w900)),
        ],
      );
}

class _SeverityStatus extends StatelessWidget {
  const _SeverityStatus({required this.agriCam, required this.isPlus});

  final Map<String, dynamic> agriCam;
  final bool isPlus;

  @override
  Widget build(BuildContext context) {
    if (!isPlus) {
      return const _MetricRow(
        label: 'Mức độ tổn thương',
        value: 'Có trong gói Plus',
      );
    }
    final severity = (agriCam['severity_percent'] as num?)?.toDouble();
    final reliability = agriCam['reliability']?.toString();
    if (severity != null) {
      final reliabilityText =
          reliability == 'reliable' ? 'Đáng tin cậy' : 'Cần kiểm tra lại';
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _MetricRow(
            label: 'Mức độ tổn thương',
            value: '${severity.toStringAsFixed(1)}%',
          ),
          const SizedBox(height: 5),
          Text(
            reliabilityText,
            style: TextStyle(
              color: reliability == 'reliable'
                  ? AppTheme.safeGreen
                  : AppTheme.warningOrange,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ],
      );
    }

    final message = switch (reliability) {
      'not_applicable' => 'Không áp dụng cho nhóm sâu hại, ốc hoặc cỏ.',
      'review_required' => 'Cần chụp lại hoặc nhờ cán bộ kiểm tra.',
      _ => 'Đang hiệu chuẩn trên dữ liệu thực địa — chưa công bố % tổn thương.',
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Text(
          'Mức độ tổn thương',
          style: TextStyle(
              color: AppTheme.textSecondary, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 5),
        Text(
          message,
          style: const TextStyle(
              color: AppTheme.textPrimary,
              fontWeight: FontWeight.w700,
              height: 1.35),
        ),
      ],
    );
  }
}

class _ImageExplanation extends StatelessWidget {
  const _ImageExplanation({
    required this.imageFile,
    required this.url,
    required this.caption,
  });

  final File imageFile;
  final String? url;
  final String caption;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: DecoratedBox(
              decoration: BoxDecoration(color: AppTheme.cardSolid),
              child: url == null
                  ? Image.file(imageFile,
                      fit: BoxFit.cover, width: double.infinity)
                  : Image.network(
                      '${EnvironmentConfig.apiBaseUrl}$url',
                      fit: BoxFit.cover,
                      width: double.infinity,
                      errorBuilder: (_, __, ___) => const Center(
                        child: Icon(Icons.broken_image_outlined, size: 40),
                      ),
                    ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            color: AppTheme.cardSolid,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.moss.withValues(alpha: 0.08)),
          ),
          child: Row(
            children: <Widget>[
              const Icon(Icons.info_outline_rounded,
                  color: AppTheme.moss, size: 18),
              const SizedBox(width: 9),
              Expanded(
                child: Text(
                  caption,
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _IPMCard extends StatelessWidget {
  const _IPMCard({required this.ipmAdvice});

  final String ipmAdvice;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: AppTheme.moss,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Row(
              children: <Widget>[
                Icon(Icons.eco_rounded, color: AppTheme.neonLeaf),
                SizedBox(width: 10),
                Text(
                  'Khuyến nghị IPM',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w900),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Text(
              ipmAdvice,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.88),
                height: 1.5,
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
}
