import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../../core/config/environment_config.dart';
import '../../core/theme/app_theme.dart';
import '../../screens/privacy_screen.dart';
import '../../services/auth_service.dart';
import '../../services/notification_service.dart';
import '../widgets/app_card.dart';
import 'login_screen.dart';
import 'notifications_screen.dart';
import 'profile_edit_screen.dart';
import 'history_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Future<Map<String, dynamic>?>? _profileFuture;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final auth = context.read<AuthService>();
    _profileFuture ??= auth.getProfile();
  }

  Future<void> _clearCache() async {
    final temporary = await getTemporaryDirectory();
    if (await temporary.exists()) {
      for (final entity in temporary.listSync()) {
        try {
          await entity.delete(recursive: true);
        } catch (_) {
          // Một số file hệ thống có thể bị khóa; giữ app hoạt động bình thường.
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
            content: const Text(
                'Bạn sẽ cần đăng nhập lại để dùng các chức năng cần tài khoản.'),
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

  @override
  Widget build(BuildContext context) {
    final authenticated = context.watch<AuthService>().isAuthenticated;
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('Hồ sơ'),
        actions: <Widget>[
          if (authenticated)
            IconButton(
              tooltip: 'Chỉnh sửa hồ sơ',
              onPressed: _editProfile,
              icon: const Icon(Icons.edit_outlined),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
        children: <Widget>[
          if (authenticated)
            _SignedInHeader(future: _profileFuture)
          else
            _SignedOutHeader(onLogin: _openLogin),
          const SizedBox(height: 22),
          const Text('Cài đặt',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          _SettingTile(
            icon: Icons.language_rounded,
            title: 'Ngôn ngữ',
            subtitle: 'Tiếng Việt',
            onTap: _showLanguageInfo,
          ),
          _SettingTile(
            icon: Icons.notifications_outlined,
            title: 'Thông báo',
            subtitle: context.watch<NotificationService>().unreadCount > 0
                ? '${context.watch<NotificationService>().unreadCount} thông báo chưa đọc'
                : 'Không có thông báo mới',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                  builder: (_) => const NotificationsScreen()),
            ),
          ),
          _SettingTile(
            icon: Icons.history_rounded,
            title: 'Lịch sử quét',
            subtitle: 'Xem lượt đã phân tích và ảnh đang chờ gửi',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const HistoryScreen()),
            ),
          ),
          _SettingTile(
            icon: Icons.dns_outlined,
            title: 'Máy chủ',
            subtitle: EnvironmentConfig.displayBaseUrl,
            onTap: _showServerInfo,
          ),
          _SettingTile(
            icon: Icons.lock_outline_rounded,
            title: 'Quyền riêng tư',
            subtitle: 'Cách RiceAI sử dụng ảnh và dữ liệu',
            onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => const PrivacyScreen())),
          ),
          _SettingTile(
            icon: Icons.delete_sweep_outlined,
            title: 'Xóa bộ nhớ đệm',
            subtitle: 'Chỉ xóa tệp tạm, không xóa tài khoản',
            destructive: true,
            onTap: _clearCache,
          ),
          if (authenticated) ...<Widget>[
            const SizedBox(height: 22),
            const Text('Tài khoản',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
            const SizedBox(height: 10),
            _SettingTile(
              icon: Icons.logout_rounded,
              title: 'Đăng xuất',
              subtitle: 'Thoát khỏi tài khoản hiện tại',
              destructive: true,
              onTap: _logout,
            ),
          ],
          const SizedBox(height: 26),
          const Center(
              child: Text(
                  'RiceAI • Phiên bản thử nghiệm\nHỗ trợ nhận diện 19 nhóm bệnh và đối tượng lúa',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: AppTheme.textMuted, fontSize: 11, height: 1.5))),
        ],
      ),
    );
  }

  void _openLogin() => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => const LoginScreen()));

  void _showLanguageInfo() => showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Ngôn ngữ'),
          content: const Text(
              'Giao diện hiện hỗ trợ tiếng Việt. Các bản dịch khác sẽ được bổ sung sau khi nội dung chuyên môn được hiệu đính.'),
          actions: <Widget>[
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Đã hiểu'))
          ],
        ),
      );

  void _showServerInfo() => showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Cấu hình máy chủ'),
          content: const Text(
              'Địa chỉ API được cấu hình khi build/chạy ứng dụng, không nhập tay trong app để tránh gửi ảnh tới nhầm máy chủ.'),
          actions: <Widget>[
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Đã hiểu'))
          ],
        ),
      );
}

class _SignedOutHeader extends StatelessWidget {
  const _SignedOutHeader({required this.onLogin});
  final VoidCallback onLogin;
  @override
  Widget build(BuildContext context) => AppCard(
        child: Row(children: <Widget>[
          const CircleAvatar(
              radius: 28,
              backgroundColor: AppTheme.cardBeige,
              child: Icon(Icons.person_outline_rounded, color: AppTheme.moss)),
          const SizedBox(width: 14),
          const Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                Text('Bạn chưa đăng nhập',
                    style:
                        TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                SizedBox(height: 3),
                Text('Đăng nhập bằng email hoặc Google để đồng bộ dữ liệu.',
                    style:
                        TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
              ])),
          FilledButton(onPressed: onLogin, child: const Text('Đăng nhập')),
        ]),
      );
}

class _SignedInHeader extends StatelessWidget {
  const _SignedInHeader({required this.future});
  final Future<Map<String, dynamic>?>? future;
  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>?>(
        future: future,
        builder: (context, snapshot) {
          final user = FirebaseAuth.instance.currentUser;
          final account = user?.isAnonymous == true
              ? 'Chế độ dùng thử — không đồng bộ giữa thiết bị'
              : user?.email ?? 'Email đã xác thực';
          final name = snapshot.data?['full_name']?.toString().trim();
          final label =
              (name == null || name.isEmpty) ? 'Người dùng RiceAI' : name;
          return AppCard(
            child: Row(children: <Widget>[
              CircleAvatar(
                  radius: 29,
                  backgroundColor: AppTheme.moss,
                  child: Text(label.characters.first.toUpperCase(),
                      style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 20))),
              const SizedBox(width: 14),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                    Text(label,
                        style: const TextStyle(
                            fontWeight: FontWeight.w900, fontSize: 16)),
                    const SizedBox(height: 3),
                    Text(account,
                        style: const TextStyle(
                            color: AppTheme.textSecondary, fontSize: 12)),
                    const SizedBox(height: 5),
                    Text(
                      user?.isAnonymous == true
                          ? 'Dữ liệu dùng thử không đồng bộ sang thiết bị khác'
                          : 'Email đã được xác thực',
                      style: const TextStyle(
                          color: AppTheme.moss,
                          fontSize: 11,
                          fontWeight: FontWeight.w700),
                    ),
                  ])),
            ]),
          );
        },
      );
}

class _SettingTile extends StatelessWidget {
  const _SettingTile(
      {required this.icon,
      required this.title,
      required this.subtitle,
      required this.onTap,
      this.destructive = false});
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final bool destructive;
  @override
  Widget build(BuildContext context) {
    final color = destructive ? AppTheme.dangerRed : AppTheme.moss;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: AppCard(
        padding: EdgeInsets.zero,
        onTap: onTap,
        child: ListTile(
          leading: Icon(icon, color: color),
          title: Text(title,
              style: TextStyle(
                  fontWeight: FontWeight.w800,
                  color: destructive ? color : AppTheme.textPrimary)),
          subtitle:
              Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.chevron_right_rounded),
        ),
      ),
    );
  }
}
