import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/auth_service.dart';
import '../../services/prediction_service.dart';
import 'ai_assistant_screen.dart';
import 'camera_screen.dart';
import 'guide_screen.dart';
import 'home_screen.dart';
import 'login_screen.dart';
import 'profile_screen.dart';
import 'plus_screen.dart';

/// AppShell – khung ngoài chứa BottomNavigationBar
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  int _currentIndex = 0;
  final _predictionService = PredictionService();
  bool? _lastAuthenticated;
  bool? _sessionPlus;
  bool? _accountPlus;
  bool _staffUnlimited = false;
  bool _loadingPlan = false;
  String? _planError;
  bool _restartNoticeShown = false;
  int _planGeneration = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final authenticated = context.watch<AuthService>().isAuthenticated;
    if (_lastAuthenticated == authenticated) return;
    _lastAuthenticated = authenticated;
    _planGeneration++;
    _restartNoticeShown = false;
    if (authenticated) {
      _sessionPlus = null;
      _loadingPlan = true;
      unawaited(_loadPlan());
    } else {
      _sessionPlus = false;
      _accountPlus = false;
      _staffUnlimited = false;
      _loadingPlan = false;
      _planError = null;
    }
  }

  Future<void> _loadPlan() async {
    final generation = _planGeneration;
    try {
      final plan = await _predictionService.getPlan();
      if (!mounted ||
          generation != _planGeneration ||
          !context.read<AuthService>().isAuthenticated) {
        return;
      }
      setState(() {
        _accountPlus = plan['plan'] == 'plus';
        _sessionPlus = _accountPlus;
        _staffUnlimited = plan['unlimited'] == true;
        _loadingPlan = false;
        _planError = null;
      });
    } catch (_) {
      if (!mounted ||
          generation != _planGeneration ||
          !context.read<AuthService>().isAuthenticated) {
        return;
      }
      setState(() {
        _loadingPlan = false;
        _planError =
            'Chưa tải được gói tài khoản. Kiểm tra kết nối với máy chủ rồi thử lại.';
      });
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed &&
        _lastAuthenticated == true &&
        _sessionPlus != null &&
        !_restartNoticeShown) {
      unawaited(_checkPlanChange());
    }
  }

  Future<void> _checkPlanChange() async {
    try {
      final plan = await _predictionService.getPlan();
      if (!mounted || !context.read<AuthService>().isAuthenticated) return;
      if ((plan['plan'] == 'plus') == _accountPlus || _restartNoticeShown) {
        return;
      }
      _restartNoticeShown = true;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Gói tài khoản đã thay đổi'),
          content: const Text(
              'Hãy đóng hẳn RiceAI rồi mở lại để dùng giao diện của gói mới.'),
          actions: <Widget>[
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Đã hiểu'),
            ),
          ],
        ),
      );
    } catch (_) {
      // Keep the current mode if the laptop is temporarily offline.
    }
  }

  void _onTabTapped(int index) {
    HapticFeedback.lightImpact();
    setState(() => _currentIndex = index);
  }

  void _switchStaffMode() {
    if (!_staffUnlimited || _sessionPlus == null) return;
    setState(() => _sessionPlus = !_sessionPlus!);
  }

  Future<void> _onScanFabTapped() async {
    HapticFeedback.mediumImpact();
    if (!context.read<AuthService>().isAuthenticated) {
      final signedIn = await Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(builder: (_) => const LoginScreen()),
      );
      if (signedIn != true || !mounted) return;
      await _loadPlan();
    }
    if (_sessionPlus == null) await _loadPlan();
    if (!mounted || _sessionPlus == null) return;
    Navigator.of(context).push(
      MaterialPageRoute<void>(
          builder: (_) => _sessionPlus == true
              ? const PlusScreen(openCameraOnStart: true)
              : const CameraScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authenticated = context.watch<AuthService>().isAuthenticated;
    final screens = <Widget>[
      HomeScreen(
        plusMode: authenticated && _sessionPlus == true,
        staffCanSwitch: authenticated && _staffUnlimited,
        onSwitchMode: _switchStaffMode,
      ),
      const AiAssistantScreen(),
      const GuideScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      body: Stack(children: <Widget>[
        IndexedStack(index: _currentIndex, children: screens),
        if (authenticated && (_loadingPlan || _sessionPlus == null))
          Positioned.fill(
            child: ColoredBox(
              color: AppTheme.porcelain,
              child: _loadingPlan
                  ? const Center(child: CircularProgressIndicator())
                  : Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            Text(_planError ?? 'Chưa tải được gói tài khoản.',
                                textAlign: TextAlign.center),
                            const SizedBox(height: 12),
                            FilledButton(
                                onPressed: () => unawaited(_loadPlan()),
                                child: const Text('Thử lại')),
                          ],
                        ),
                      ),
                    ),
            ),
          ),
      ]),
      bottomNavigationBar: _BottomNav(
        currentIndex: _currentIndex,
        onTap: _onTabTapped,
        onFabTap: () => unawaited(_onScanFabTapped()),
      ),
    );
  }
}

// ── Bottom Nav ──────────────────────────────────

class _BottomNav extends StatelessWidget {
  const _BottomNav({
    required this.currentIndex,
    required this.onTap,
    required this.onFabTap,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;
  final VoidCallback onFabTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.cardSolid,
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppTheme.moss.withValues(alpha: 0.06),
            blurRadius: 24,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: <Widget>[
              _NavItem(
                icon: Icons.home_outlined,
                activeIcon: Icons.home_rounded,
                label: 'Trang chủ',
                isActive: currentIndex == 0,
                onTap: () => onTap(0),
              ),
              _NavItem(
                icon: Icons.chat_bubble_outline_rounded,
                activeIcon: Icons.chat_bubble_rounded,
                label: 'Trợ lý',
                isActive: currentIndex == 1,
                onTap: () => onTap(1),
              ),

              // FAB center scan
              _ScanFab(onTap: onFabTap),

              _NavItem(
                icon: Icons.menu_book_outlined,
                activeIcon: Icons.menu_book_rounded,
                label: 'Cẩm nang',
                isActive: currentIndex == 2,
                onTap: () => onTap(2),
              ),
              _NavItem(
                icon: Icons.person_outline_rounded,
                activeIcon: Icons.person_rounded,
                label: 'Hồ sơ',
                isActive: currentIndex == 3,
                onTap: () => onTap(3),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final IconData activeIcon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: SizedBox(
        width: 64,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: Icon(
                isActive ? activeIcon : icon,
                key: ValueKey<bool>(isActive),
                color: isActive ? AppTheme.moss : AppTheme.textMuted,
                size: 24,
              ),
            ),
            const SizedBox(height: 3),
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 200),
              style: TextStyle(
                fontSize: 10,
                fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                color: isActive ? AppTheme.moss : AppTheme.textMuted,
              ),
              child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScanFab extends StatelessWidget {
  const _ScanFab({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56,
        height: 56,
        margin: const EdgeInsets.only(bottom: 4),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: <Color>[AppTheme.moss, AppTheme.mossMid],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          shape: BoxShape.circle,
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: AppTheme.moss.withValues(alpha: 0.35),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: const Icon(Icons.qr_code_scanner_rounded,
            color: AppTheme.neonLeaf, size: 24),
      ),
    );
  }
}
