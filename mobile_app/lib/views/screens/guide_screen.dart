import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/theme/app_theme.dart';
import '../../models/disease_model.dart';
import '../../services/disease_library_service.dart';
import '../widgets/app_card.dart';
import 'guide_detail_screen.dart';

class GuideScreen extends StatefulWidget {
  const GuideScreen({super.key});

  @override
  State<GuideScreen> createState() => _GuideScreenState();
}

class _GuideScreenState extends State<GuideScreen> {
  final _service = DiseaseLibraryService();
  final _search = TextEditingController();
  Future<List<DiseaseInfo>>? _future;
  DiseaseCategory? _selected;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _future = _service.getDiseases();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _reload() => setState(() => _future = _service.getDiseases());

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppTheme.porcelain,
        appBar: AppBar(
            automaticallyImplyLeading: false,
            title: const Text('Cẩm nang bệnh')),
        body: FutureBuilder<List<DiseaseInfo>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(
                  child: CircularProgressIndicator(color: AppTheme.moss));
            }
            if (snapshot.hasError) {
              return _ErrorState(
                  onRetry: _reload, error: snapshot.error.toString());
            }
            final all = snapshot.data ?? const <DiseaseInfo>[];
            final visible = all.where((disease) {
              final matchesCategory =
                  _selected == null || disease.category == _selected;
              final query = _query.toLowerCase();
              final matchesQuery = query.isEmpty ||
                  disease.name.toLowerCase().contains(query) ||
                  disease.nameEn.toLowerCase().contains(query);
              return matchesCategory && matchesQuery;
            }).toList(growable: false);
            return Column(
              children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 10),
                  child: TextField(
                    controller: _search,
                    onChanged: (value) => setState(() => _query = value.trim()),
                    decoration: InputDecoration(
                      hintText: 'Tìm trong ${all.length} nhóm bệnh/đối tượng',
                      prefixIcon: const Icon(Icons.search_rounded),
                      suffixIcon: _query.isEmpty
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.close_rounded),
                              onPressed: () {
                                _search.clear();
                                setState(() => _query = '');
                              },
                            ),
                    ),
                  ),
                ),
                SizedBox(
                  height: 42,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    children: <Widget>[
                      _CategoryChip(
                          label: 'Tất cả (${all.length})',
                          selected: _selected == null,
                          onTap: () => setState(() => _selected = null)),
                      ...DiseaseCategory.values.map(
                        (category) => _CategoryChip(
                          label:
                              '${category.label} (${all.where((d) => d.category == category).length})',
                          selected: _selected == category,
                          onTap: () => setState(() => _selected = category),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: visible.isEmpty
                      ? const Center(child: Text('Không tìm thấy mục phù hợp.'))
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(20, 14, 20, 32),
                          itemCount: visible.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 10),
                          itemBuilder: (context, index) =>
                              _DiseaseCard(disease: visible[index])
                                  .animate(
                                      delay: Duration(
                                          milliseconds: 35 * index.clamp(0, 8)))
                                  .fade()
                                  .slideY(begin: .04),
                        ),
                ),
              ],
            );
          },
        ),
      );
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip(
      {required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: ChoiceChip(
          label: Text(label),
          selected: selected,
          onSelected: (_) => onTap(),
          selectedColor: AppTheme.moss.withValues(alpha: .16),
          labelStyle: TextStyle(
              color: selected ? AppTheme.moss : AppTheme.textSecondary,
              fontWeight: FontWeight.w700),
          side: BorderSide(
              color: selected ? AppTheme.moss : AppTheme.borderBeige),
        ),
      );
}

class _DiseaseCard extends StatelessWidget {
  const _DiseaseCard({required this.disease});
  final DiseaseInfo disease;

  @override
  Widget build(BuildContext context) {
    final isLeaf = disease.category == DiseaseCategory.leafDisease;
    final accent = isLeaf ? AppTheme.moss : AppTheme.warningOrange;
    return AppCard(
      padding: EdgeInsets.zero,
      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => GuideDetailScreen(disease: disease))),
      child: Row(
        children: <Widget>[
          Container(
            width: 78,
            height: 98,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                  colors: isLeaf
                      ? const <Color>[AppTheme.moss, AppTheme.mossMid]
                      : const <Color>[Color(0xFF9A6A23), Color(0xFFC49D4B)]),
              borderRadius:
                  const BorderRadius.horizontal(left: Radius.circular(20)),
            ),
            child: Icon(
                isLeaf ? Icons.eco_outlined : Icons.pest_control_rounded,
                color: Colors.white,
                size: 34),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(disease.category.label.toUpperCase(),
                        style: TextStyle(
                            color: accent,
                            fontSize: 10,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 5),
                    Text(disease.name,
                        style: const TextStyle(
                            fontWeight: FontWeight.w900,
                            color: AppTheme.textPrimary)),
                    const SizedBox(height: 4),
                    Text(disease.shortDesc,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 12,
                            height: 1.35,
                            color: AppTheme.textSecondary)),
                  ]),
            ),
          ),
          const Padding(
              padding: EdgeInsets.only(right: 8),
              child:
                  Icon(Icons.chevron_right_rounded, color: AppTheme.textMuted)),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry, required this.error});
  final VoidCallback onRetry;
  final String error;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
            const Icon(Icons.cloud_off_rounded,
                size: 42, color: AppTheme.textMuted),
            const SizedBox(height: 12),
            const Text('Không tải được Cẩm nang',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
            const SizedBox(height: 6),
            Text(error,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    color: AppTheme.textSecondary, fontSize: 12)),
            const SizedBox(height: 16),
            FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Thử lại')),
          ]),
        ),
      );
}
