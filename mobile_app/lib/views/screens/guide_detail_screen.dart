import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/theme/app_theme.dart';
import '../../models/disease_model.dart';
import '../widgets/app_card.dart';

class GuideDetailScreen extends StatelessWidget {
  const GuideDetailScreen({super.key, required this.disease});

  final DiseaseInfo disease;

  @override
  Widget build(BuildContext context) {
    final bool isLeaf = disease.category == DiseaseCategory.leafDisease;
    final Color accent = isLeaf ? AppTheme.moss : AppTheme.warningOrange;

    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      body: CustomScrollView(
        slivers: <Widget>[
          // ── Hero SliverAppBar ─────────────────────
          SliverAppBar(
            expandedHeight: 220,
            pinned: true,
            backgroundColor: AppTheme.moss,
            foregroundColor: Colors.white,
            iconTheme: const IconThemeData(color: Colors.white),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[AppTheme.moss, AppTheme.mossMid],
                  ),
                ),
                child: Stack(
                  children: <Widget>[
                    // Background icon
                    Positioned(
                      right: -20,
                      bottom: -20,
                      child: Icon(
                        isLeaf ? Icons.eco_rounded : Icons.bug_report_rounded,
                        size: 200,
                        color: Colors.white.withValues(alpha: 0.06),
                      ),
                    ),
                    // Content
                    Positioned(
                      left: 24,
                      right: 24,
                      bottom: 30,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(100),
                            ),
                            child: Text(
                              disease.category.label.toUpperCase(),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1,
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            disease.name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.5,
                              height: 1.15,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            disease.nameEn,
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.72),
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            actions: <Widget>[
              IconButton(
                onPressed: () {},
                icon: const Icon(Icons.bookmark_border_rounded),
                tooltip: 'Lưu',
              ),
              const SizedBox(width: 8),
            ],
          ),

          // ── Content ───────────────────────────────
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
            sliver: SliverList(
              delegate: SliverChildListDelegate(<Widget>[
                // Short desc
                Text(
                  disease.shortDesc,
                  style: const TextStyle(
                    fontSize: 15,
                    color: AppTheme.textSecondary,
                    height: 1.55,
                    fontWeight: FontWeight.w500,
                  ),
                ).animate().fade(),

                const SizedBox(height: 24),

                _InfoSection(
                  icon: Icons.search_rounded,
                  title: 'Triệu chứng nhận biết',
                  content: disease.symptoms,
                  accentColor: accent,
                  delay: 80,
                ),

                const SizedBox(height: 14),

                _InfoSection(
                  icon: Icons.wb_cloudy_outlined,
                  title: 'Điều kiện phát sinh',
                  content: disease.conditions,
                  accentColor: AppTheme.warningOrange,
                  delay: 120,
                ),

                const SizedBox(height: 14),

                _InfoSection(
                  icon: Icons.shield_outlined,
                  title: 'Cách phòng ngừa',
                  content: disease.prevention,
                  accentColor: AppTheme.safeGreen,
                  delay: 160,
                ),

                const SizedBox(height: 14),

                _InfoSection(
                  icon: Icons.local_pharmacy_outlined,
                  title: 'Khuyến nghị xử lý',
                  content: disease.treatment,
                  accentColor: AppTheme.dangerRed,
                  delay: 200,
                ),

                if (!disease.severityApplicable) ...<Widget>[
                  const SizedBox(height: 16),
                  AppCard(
                    color: AppTheme.cardBeige,
                    child: Row(
                      children: <Widget>[
                        const Icon(Icons.info_outline_rounded,
                            color: AppTheme.textMuted, size: 18),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Text(
                            'Đánh giá mức độ tổn thương lá: Không áp dụng cho sâu hại.',
                            style: TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ).animate(delay: 240.ms).fade(),
                ],

                const SizedBox(height: 24),

                // Back CTA
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.arrow_back_rounded, size: 18),
                    label: const Text('Quay lại cẩm nang'),
                  ),
                ).animate(delay: 280.ms).fade().slideY(begin: 0.2),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoSection extends StatelessWidget {
  const _InfoSection({
    required this.icon,
    required this.title,
    required this.content,
    required this.accentColor,
    this.delay = 0,
  });

  final IconData icon;
  final String title;
  final String content;
  final Color accentColor;
  final int delay;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: accentColor, size: 19),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            content,
            style: const TextStyle(
              fontSize: 13,
              color: AppTheme.textSecondary,
              height: 1.55,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    ).animate(delay: Duration(milliseconds: delay)).fade().slideY(begin: 0.08);
  }
}
