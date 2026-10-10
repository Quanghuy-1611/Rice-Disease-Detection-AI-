import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/image_service.dart';
import '../../services/connectivity_service.dart';
import '../../services/notification_service.dart';
import '../../services/offline_queue_service.dart';
import '../../services/prediction_service.dart';
import '../../services/auth_service.dart';
import '../widgets/app_card.dart';
import '../widgets/section_title.dart';
import 'analysis_screen.dart';
import 'camera_screen.dart';
import 'history_screen.dart';
import 'notifications_screen.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  String _analysisMode = 'basic';
  final _connectivityService = ConnectivityService();
  final _offlineQueueService = OfflineQueueService();
  final _predictionService = PredictionService();
  StreamSubscription<bool>? _connectionSubscription;
  Future<List<Map<String, dynamic>>>? _recentHistory;
  bool? _lastAuthenticated;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _connectionSubscription =
        _connectivityService.onConnectionChanged.listen((connected) {
      if (connected) unawaited(_syncOfflineQueue());
    });
    unawaited(_syncOfflineQueue());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final signedIn = context.watch<AuthService>().isAuthenticated;
    if (_lastAuthenticated != signedIn) {
      _lastAuthenticated = signedIn;
      _recentHistory = signedIn
          ? _predictionService.getHistory()
          : Future.value(const <Map<String, dynamic>>[]);
      if (signedIn) unawaited(_syncOfflineQueue());
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_syncOfflineQueue());
    }
  }

  Future<void> _syncOfflineQueue() async {
    try {
      if (!context.read<AuthService>().isAuthenticated) return;
      if (!await _connectivityService.isConnected) return;
      final result = await _offlineQueueService.retryPending();
      if (result.sent > 0 && mounted) {
        await context
            .read<NotificationService>()
            .addQueueSynced(count: result.sent);
        _reloadRecentHistory();
      }
    } catch (_) {
      // A later connectivity change will safely try again; never interrupt home UI.
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _connectionSubscription?.cancel();
    super.dispose();
  }

  Future<void> _openCamera(BuildContext context) async {
    if (!await _requireEmailLogin(context) || !context.mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CameraScreen(analysisMode: _analysisMode),
      ),
    );
    _reloadRecentHistory();
  }

  Future<void> _pickFromGallery(BuildContext context) async {
    if (!await _requireEmailLogin(context) || !context.mounted) return;
    final imageFile = await ImageService().pickFromGallery();
    if (imageFile == null || !context.mounted) return;

    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => AnalysisScreen(
          imageFile: imageFile,
          analysisMode: _analysisMode,
        ),
      ),
    );
    _reloadRecentHistory();
  }

  void _reloadRecentHistory() {
    if (!mounted) return;
    setState(() => _recentHistory = context.read<AuthService>().isAuthenticated
        ? _predictionService.getHistory()
        : Future.value(const <Map<String, dynamic>>[]));
  }

  Future<void> _openHistory(BuildContext context) async {
    if (!await _requireEmailLogin(context) || !context.mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const HistoryScreen()),
    );
    _reloadRecentHistory();
  }

  Future<bool> _requireEmailLogin(BuildContext context) async {
    if (context.read<AuthService>().isAuthenticated) return true;
    final signedIn = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(builder: (_) => const LoginScreen()),
    );
    if (signedIn == true) _reloadRecentHistory();
    return signedIn == true;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      body: SafeArea(
        child: CustomScrollView(
          slivers: <Widget>[
            // ── Header ──────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: const _HomeHeader()
                    .animate()
                    .fade(duration: 350.ms)
                    .slideY(begin: -0.05),
              ),
            ),

            // ── Hero Card ───────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
                child: _HeroCard(
                  onCameraTap: () => unawaited(_openCamera(context)),
                  onGalleryTap: () => _pickFromGallery(context),
                  analysisMode: _analysisMode,
                  onAnalysisModeChanged: (value) {
                    setState(() => _analysisMode = value);
                  },
                )
                    .animate(delay: 60.ms)
                    .fade(duration: 400.ms)
                    .slideY(begin: 0.06),
              ),
            ),

            // ── Recent Results ───────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 26, 20, 0),
                child: SectionTitle(
                  title: 'Lượt quét gần đây',
                  action: 'Xem tất cả',
                  onActionTap: () => unawaited(_openHistory(context)),
                ).animate(delay: 160.ms).fade(),
              ),
            ),

            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(0, 12, 0, 0),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: _RecentHistory(
                    future: _recentHistory,
                    onOpenHistory: () => unawaited(_openHistory(context)),
                  ),
                ).animate(delay: 200.ms).fade(),
              ),
            ),

            // ── Info Card ────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
                child: const _AiScopeCard()
                    .animate(delay: 240.ms)
                    .fade()
                    .slideY(begin: 0.06),
              ),
            ),

            // ── Safety note ──────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 30),
                child: const _SafetyNote().animate(delay: 340.ms).fade(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── HEADER ──────────────────────────────────────

class _HomeHeader extends StatelessWidget {
  const _HomeHeader();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        // Logo container
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: <Color>[AppTheme.moss, AppTheme.mossMid],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(13),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: AppTheme.moss.withValues(alpha: 0.25),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child:
              const Icon(Icons.eco_rounded, color: AppTheme.neonLeaf, size: 24),
        ),
        const SizedBox(width: 12),

        // Title
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'RiceAI',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.4,
                ),
              ),
              Text(
                'Chẩn đoán bệnh lúa thông minh',
                style: TextStyle(
                  color: AppTheme.textMuted,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),

        Consumer<NotificationService>(
          builder: (context, notifications, _) => Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppTheme.cardSolid,
              shape: BoxShape.circle,
              border: Border.all(color: AppTheme.borderBeige),
            ),
            child: IconButton(
              tooltip: 'Thông báo',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                    builder: (_) => const NotificationsScreen()),
              ),
              icon: Stack(
                clipBehavior: Clip.none,
                children: <Widget>[
                  const Icon(Icons.notifications_outlined,
                      color: AppTheme.textSecondary, size: 20),
                  if (notifications.unreadCount > 0)
                    Positioned(
                      top: -3,
                      right: -4,
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                            color: AppTheme.dangerRed, shape: BoxShape.circle),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ── HERO CARD ───────────────────────────────────

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.onCameraTap,
    required this.onGalleryTap,
    required this.analysisMode,
    required this.onAnalysisModeChanged,
  });

  final VoidCallback onCameraTap;
  final VoidCallback onGalleryTap;
  final String analysisMode;
  final ValueChanged<String> onAnalysisModeChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[AppTheme.moss, AppTheme.mossDark],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppTheme.moss.withValues(alpha: 0.3),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Stack(
          children: <Widget>[
            // Background decoration
            Positioned(
              right: -40,
              top: -40,
              child: Container(
                width: 200,
                height: 200,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.neonLeaf.withValues(alpha: 0.07),
                ),
              ),
            ),
            Positioned(
              right: -10,
              bottom: -30,
              child: Icon(
                Icons.eco_rounded,
                size: 180,
                color: Colors.white.withValues(alpha: 0.05),
              ),
            ),
            // Rice grain dots decoration
            ..._buildDots(),

            // Content
            Padding(
              padding: const EdgeInsets.all(22),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  // Tag
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(
                          color: Colors.white.withValues(alpha: 0.15)),
                    ),
                    child: const Text(
                      'NÔNG NGHIỆP THÔNG MINH',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 9.5,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Headline
                  const Text(
                    'Bảo vệ\nmùa màng của bạn',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                      height: 1.1,
                      letterSpacing: -0.6,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Phát hiện sớm bệnh hại lúa với AI',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.75),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 16),

                  _AnalysisModeSelector(
                    value: analysisMode,
                    onChanged: onAnalysisModeChanged,
                  ),
                  const SizedBox(height: 16),

                  // Action buttons
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: _HeroCta(
                          icon: Icons.camera_alt_rounded,
                          label: 'Chụp ảnh\nlá lúa',
                          isPrimary: true,
                          onTap: onCameraTap,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _HeroCta(
                          icon: Icons.photo_library_outlined,
                          label: 'Chọn từ\nthư viện',
                          isPrimary: false,
                          onTap: onGalleryTap,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildDots() {
    final List<Map<String, double>> positions = <Map<String, double>>[
      <String, double>{'right': 36, 'top': 24, 'size': 10},
      <String, double>{'right': 72, 'top': 50, 'size': 6},
      <String, double>{'right': 28, 'top': 58, 'size': 18},
    ];
    return positions
        .map(
          (Map<String, double> p) => Positioned(
            right: p['right'],
            top: p['top'],
            child: Container(
              width: p['size'],
              height: p['size'],
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.neonLeaf.withValues(alpha: 0.6),
              ),
            ),
          ),
        )
        .toList();
  }
}

class _AnalysisModeSelector extends StatelessWidget {
  const _AnalysisModeSelector({
    required this.value,
    required this.onChanged,
  });

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
      ),
      child: Row(
        children: <Widget>[
          _ModeChoice(
            selected: value == 'basic',
            icon: Icons.visibility_outlined,
            label: 'Basic · Grad-CAM',
            onTap: () => onChanged('basic'),
          ),
        ],
      ),
    );
  }
}

class _ModeChoice extends StatelessWidget {
  const _ModeChoice({
    required this.selected,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final bool selected;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Material(
        color: selected
            ? Colors.white.withValues(alpha: 0.16)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(9),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(9),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Icon(icon,
                    color: selected ? AppTheme.neonLeaf : Colors.white70,
                    size: 15),
                const SizedBox(width: 5),
                Flexible(
                  child: Text(
                    label,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 10.5,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HeroCta extends StatelessWidget {
  const _HeroCta({
    required this.icon,
    required this.label,
    required this.isPrimary,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool isPrimary;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color:
          isPrimary ? AppTheme.neonLeaf : Colors.white.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          child: Row(
            children: <Widget>[
              Icon(
                icon,
                color: isPrimary ? AppTheme.moss : Colors.white,
                size: 20,
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  style: TextStyle(
                    color: isPrimary ? AppTheme.moss : Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    height: 1.3,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── RECENT CARD ─────────────────────────────────

class _RecentHistory extends StatelessWidget {
  const _RecentHistory({required this.future, required this.onOpenHistory});

  final Future<List<Map<String, dynamic>>>? future;
  final VoidCallback onOpenHistory;

  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const SizedBox(
              height: 94,
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            );
          }
          if (snapshot.hasError) return _EmptyHistoryCard(onTap: onOpenHistory);
          final items = snapshot.data ?? const <Map<String, dynamic>>[];
          if (items.isEmpty) return _EmptyHistoryCard(onTap: onOpenHistory);
          return SizedBox(
            height: 130,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: items.length > 5 ? 5 : items.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (context, index) => _RecentCard(
                item: items[index],
                index: index,
                onTap: onOpenHistory,
              ),
            ),
          );
        },
      );
}

class _EmptyHistoryCard extends StatelessWidget {
  const _EmptyHistoryCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => AppCard(
        color: AppTheme.cardBeige,
        onTap: onTap,
        child: const Row(
          children: <Widget>[
            Icon(Icons.history_rounded, color: AppTheme.moss),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Chưa có lượt quét nào trên thiết bị này. Hãy chụp hoặc chọn ảnh lá lúa để bắt đầu.',
                style: TextStyle(color: AppTheme.textSecondary, height: 1.4),
              ),
            ),
          ],
        ),
      );
}

class _RecentCard extends StatelessWidget {
  const _RecentCard({
    required this.item,
    required this.index,
    required this.onTap,
  });

  final Map<String, dynamic> item;
  final int index;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 150,
        decoration: BoxDecoration(
          color: AppTheme.cardSolid,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppTheme.borderBeige),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: AppTheme.moss.withValues(alpha: 0.04),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            // Thumbnail
            ClipRRect(
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(17)),
              child: Container(
                height: 72,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: index % 2 == 0
                        ? <Color>[
                            const Color(0xFF2B6B44),
                            const Color(0xFF8BC34A)
                          ]
                        : <Color>[
                            const Color(0xFF4A7B3A),
                            const Color(0xFF9CCC65)
                          ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: const Center(
                  child: Icon(Icons.eco_rounded, color: Colors.white, size: 34),
                ),
              ),
            ),

            // Info
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    item['prediction']?.toString() ?? 'Không xác định',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    _formatDate(
                      DateTime.tryParse(item['created_at']?.toString() ?? ''),
                    ),
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppTheme.textMuted,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime? d) => d == null
      ? 'Không rõ ngày'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
}

// ── AI SCOPE CARD ────────────────────────────────

class _AiScopeCard extends StatelessWidget {
  const _AiScopeCard();

  @override
  Widget build(BuildContext context) {
    return AppCard(
      color: AppTheme.cardBeige,
      child: Row(
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppTheme.moss.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.auto_awesome_rounded,
                color: AppTheme.moss, size: 22),
          ),
          const SizedBox(width: 14),
          const Expanded(
            child: Text(
              'AI hỗ trợ nhận diện 7 nhóm bệnh và đối tượng trên ruộng lúa.',
              style: TextStyle(
                fontSize: 13,
                color: AppTheme.textSecondary,
                height: 1.45,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── SAFETY NOTE ─────────────────────────────────

class _SafetyNote extends StatelessWidget {
  const _SafetyNote();

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Icon(Icons.info_outline_rounded,
            color: AppTheme.textMuted, size: 15),
        const SizedBox(width: 8),
        const Expanded(
          child: Text(
            'Kết quả AI là thông tin hỗ trợ. Hãy đối chiếu điều kiện ruộng và tư vấn chuyên môn trước khi xử lý.',
            style: TextStyle(
              color: AppTheme.textMuted,
              fontSize: 11,
              height: 1.5,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }
}
