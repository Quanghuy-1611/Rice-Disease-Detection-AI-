import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../../core/config/environment_config.dart';
import '../../core/theme/app_theme.dart';
import '../../screens/privacy_screen.dart';
import '../../services/auth_service.dart';
import '../../services/notification_service.dart';
import 'history_screen.dart';
import 'login_screen.dart';
import 'notifications_screen.dart';
import 'profile_edit_screen.dart';
import 'server_settings_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Future<Map<String, dynamic>?>? _profileFuture;
  bool? _lastAuthenticated;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final auth = context.watch<AuthService>();
    if (_lastAuthenticated != auth.isAuthenticated) {
      _lastAuthenticated = auth.isAuthenticated;
      _profileFuture = auth.isAuthenticated ? auth.getProfile() : null;
    }
  }

  Future<void> _clearCache() async {
    final temporary = await getTemporaryDirectory();
    if (await temporary.exists()) {
      for (final entity in temporary.listSync()) {
        try {
          await entity.delete(recursive: true);
        } catch (_) {
          // A file may still be in use; other temporary files can be cleared.
        }
      }
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã xóa các tệp tạm của ứng dụng.')));
  }

  Future<void> _logout() async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Đăng xuất?'),
            content: const Text('Bạn sẽ cần đăng nhập lại để dùng RiceAI.'),
            actions: <Widget>[
              TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Hủy')),
              FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Đăng xuất')),
            ],
          ),
        ) ??
        false;
    if (!confirmed || !mounted) return;
    await context.read<AuthService>().logout();
    if (mounted) setState(() => _profileFuture = null);
  }

  Future<void> _editProfile() async {
    try {
      final profile = await context.read<AuthService>().getProfile();
      if (!mounted) return;
      final changed = await Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(
          builder: (_) => ProfileEditScreen(
            initialName: profile?['full_name']?.toString() ?? '',
          ),
        ),
      );
      if (changed == true && mounted) {
        setState(
            () => _profileFuture = context.read<AuthService>().getProfile());
      }
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Không mở được hồ sơ: $error')));
    }
  }

  Future<void> _openServerSettings() async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(builder: (_) => const ServerSettingsScreen()),
    );
    if (changed == true && mounted) {
      setState(() => _profileFuture =
          context.read<AuthService>().isAuthenticated
              ? context.read<AuthService>().getProfile()
              : null);
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã kết nối máy chủ RiceAI.')));
    }
  }

  Future<void> _openHistory() async {
    if (!context.read<AuthService>().isAuthenticated) {
      final signedIn = await Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(builder: (_) => const LoginScreen()),
      );
      if (signedIn != true || !mounted) return;
    }
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(builder: (_) => const HistoryScreen()),
    );
  }

  void _showLanguageInfo() => showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Ngôn ngữ'),
          content: const Text('RiceAI hiện hỗ trợ tiếng Việt.'),
          actions: <Widget>[
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Đã hiểu')),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final authenticated = context.watch<AuthService>().isAuthenticated;
    final unread = context.watch<NotificationService>().unreadCount;
    final server = EnvironmentConfig.mode == RiceAiServerMode.local
        ? 'Gần laptop'
        : 'Internet';

    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('Hồ sơ'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 42),
        children: <Widget>[
          if (authenticated)
            _SignedInHeader(future: _profileFuture, onEdit: _editProfile)
          else
            _SignedOutHeader(
                onLogin: () => Navigator.of(context).push<bool>(
                      MaterialPageRoute<bool>(
                          builder: (_) => const LoginScreen()),
                    )),
          const SizedBox(height: 28),
          const _SectionTitle('Hoạt động'),
          const SizedBox(height: 10),
          _SettingsGroup(children: <Widget>[
            _SettingRow(
              icon: Icons.history_rounded,
              title: 'Lịch sử chẩn đoán',
              onTap: _openHistory,
            ),
            _SettingRow(
              icon: Icons.notifications_none_rounded,
              title: 'Thông báo',
              detail: unread > 0 ? '$unread mới' : null,
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                    builder: (_) => const NotificationsScreen()),
              ),
            ),
          ]),
          const SizedBox(height: 24),
          const _SectionTitle('Ứng dụng'),
          const SizedBox(height: 10),
          _SettingsGroup(children: <Widget>[
            _SettingRow(
              icon: Icons.dns_outlined,
              title: 'Máy chủ',
              detail: server,
              onTap: _openServerSettings,
            ),
            _SettingRow(
              icon: Icons.shield_outlined,
              title: 'Quyền riêng tư',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => const PrivacyScreen()),
              ),
            ),
            _SettingRow(
              icon: Icons.language_rounded,
              title: 'Ngôn ngữ',
              detail: 'Tiếng Việt',
              onTap: _showLanguageInfo,
            ),
            _SettingRow(
              icon: Icons.cleaning_services_outlined,
              title: 'Dọn dữ liệu tạm',
              onTap: _clearCache,
            ),
          ]),
          if (authenticated) ...<Widget>[
            const SizedBox(height: 24),
            TextButton.icon(
              onPressed: _logout,
              icon: const Icon(Icons.logout_rounded, size: 19),
              label: const Text('Đăng xuất'),
              style: TextButton.styleFrom(
                foregroundColor: AppTheme.dangerRed,
                alignment: Alignment.centerLeft,
                padding: const EdgeInsets.symmetric(horizontal: 4),
              ),
            ),
          ],
          const SizedBox(height: 26),
          const Center(
            child: Text('RiceAI',
                style: TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}

class _SignedOutHeader extends StatelessWidget {
  const _SignedOutHeader({required this.onLogin});
  final VoidCallback onLogin;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(20),
        decoration: _panelDecoration(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text('Chào bạn',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            const SizedBox(height: 5),
            const Text('Đăng nhập để lưu lịch sử chẩn đoán.',
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 14)),
            const SizedBox(height: 18),
            FilledButton(onPressed: onLogin, child: const Text('Đăng nhập')),
          ],
        ),
      );
}

class _SignedInHeader extends StatelessWidget {
  const _SignedInHeader({required this.future, required this.onEdit});
  final Future<Map<String, dynamic>?>? future;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>?>(
        future: future,
        builder: (context, snapshot) {
          final user = FirebaseAuth.instance.currentUser;
          final anonymous = user?.isAnonymous == true;
          final account = anonymous ? 'Tài khoản dùng thử' : user?.email ?? '';
          final name = snapshot.data?['full_name']?.toString().trim();
          final label =
              name == null || name.isEmpty ? 'Người dùng RiceAI' : name;
          return Container(
            padding: const EdgeInsets.all(20),
            decoration: _panelDecoration(),
            child: Row(
              children: <Widget>[
                CircleAvatar(
                  radius: 26,
                  backgroundColor: const Color(0xFFE8EFE4),
                  child: Text(label.characters.first.toUpperCase(),
                      style: const TextStyle(
                          color: AppTheme.moss,
                          fontSize: 22,
                          fontWeight: FontWeight.w700)),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              fontSize: 19, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 3),
                      Text(account,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              color: AppTheme.textSecondary, fontSize: 13)),
                      const SizedBox(height: 7),
                      Row(
                        children: <Widget>[
                          const Icon(Icons.check_circle_outline_rounded,
                              size: 15, color: AppTheme.mossMid),
                          const SizedBox(width: 5),
                          Text(
                              anonymous ? 'Đang dùng thử' : 'Email đã xác minh',
                              style: const TextStyle(
                                  color: AppTheme.mossMid,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600)),
                        ],
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: onEdit,
                  tooltip: 'Sửa tên hiển thị',
                  icon: const Icon(Icons.edit_outlined, size: 21),
                ),
              ],
            ),
          );
        },
      );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title);
  final String title;

  @override
  Widget build(BuildContext context) => Text(title,
      style: const TextStyle(
          color: AppTheme.textPrimary,
          fontSize: 16,
          fontWeight: FontWeight.w700));
}

class _SettingsGroup extends StatelessWidget {
  const _SettingsGroup({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _panelDecoration(),
        child: Column(
          children: <Widget>[
            for (var index = 0; index < children.length; index++) ...<Widget>[
              if (index > 0)
                const Divider(indent: 66, endIndent: 16, height: 1),
              children[index],
            ],
          ],
        ),
      );
}

class _SettingRow extends StatelessWidget {
  const _SettingRow({
    required this.icon,
    required this.title,
    required this.onTap,
    this.detail,
  });

  final IconData icon;
  final String title;
  final String? detail;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: <Widget>[
                SizedBox(
                  width: 38,
                  height: 38,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0F3EB),
                      borderRadius: BorderRadius.circular(11),
                    ),
                    child: Icon(icon, color: AppTheme.mossMid, size: 21),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(title,
                      style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w600)),
                ),
                if (detail != null) ...<Widget>[
                  Flexible(
                    child: Text(detail!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: AppTheme.textSecondary, fontSize: 12)),
                  ),
                  const SizedBox(width: 6),
                ],
                const Icon(Icons.chevron_right_rounded,
                    color: AppTheme.textMuted, size: 20),
              ],
            ),
          ),
        ),
      );
}

BoxDecoration _panelDecoration() => BoxDecoration(
      color: AppTheme.cardSolid,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: AppTheme.borderBeige),
    );
