import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config/environment_config.dart';
import '../../core/theme/app_theme.dart';
import '../../services/auth_service.dart';

class ServerSettingsScreen extends StatefulWidget {
  const ServerSettingsScreen({super.key});

  @override
  State<ServerSettingsScreen> createState() => _ServerSettingsScreenState();
}

class _ServerSettingsScreenState extends State<ServerSettingsScreen> {
  late RiceAiServerMode _mode;
  late final TextEditingController _address;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _mode = EnvironmentConfig.mode;
    _address = TextEditingController(text: EnvironmentConfig.addressFor(_mode));
  }

  @override
  void dispose() {
    _address.dispose();
    super.dispose();
  }

  void _select(RiceAiServerMode mode) {
    if (_saving || _mode == mode) return;
    setState(() {
      _mode = mode;
      _address.text = EnvironmentConfig.addressFor(mode);
      _error = null;
    });
  }

  Future<void> _save() async {
    if (_saving) return;
    final url = EnvironmentConfig.normalize(_address.text);
    if (!EnvironmentConfig.isValidServerUrl(url, _mode)) {
      setState(() => _error = _mode == RiceAiServerMode.local
          ? 'Nhập địa chỉ dạng http://IP:8015.'
          : 'Nhập địa chỉ HTTPS của máy chủ.');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });
    var reachedApi = false;
    try {
      final response = await Dio(BaseOptions(
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      )).get<Map<String, dynamic>>('$url/api/health');
      if (response.data?['status'] != 'ok' ||
          response.data?['model_classes'] is! List) {
        throw const FormatException('Địa chỉ này không phải API RiceAI.');
      }
      reachedApi = true;
      if (!mounted) return;
      await context.read<AuthService>().changeServer(_mode, url);
      if (mounted) Navigator.of(context).pop(true);
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = reachedApi
          ? 'Đã kết nối RiceAI nhưng chưa xác nhận được tài khoản.'
          : 'Chưa kết nối được. Kiểm tra Tailscale, mạng và địa chỉ.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(title: const Text('Máy chủ')),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
                children: <Widget>[
                  const Text('Kết nối RiceAI',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 25,
                          fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  const Text(
                    'Chọn máy chủ phù hợp với nơi bạn đang dùng điện thoại.',
                    style: TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 14,
                        height: 1.4),
                  ),
                  const SizedBox(height: 24),
                  _ModeOption(
                    icon: Icons.wifi_rounded,
                    title: 'Gần laptop',
                    description: 'iPhone và laptop dùng cùng mạng Wi-Fi.',
                    selected: _mode == RiceAiServerMode.local,
                    onTap: () => _select(RiceAiServerMode.local),
                  ),
                  const SizedBox(height: 10),
                  _ModeOption(
                    icon: Icons.public_rounded,
                    title: 'Internet',
                    description: 'Dùng khi đi xa. Bật Tailscale trên iPhone.',
                    selected: _mode == RiceAiServerMode.internet,
                    onTap: () => _select(RiceAiServerMode.internet),
                  ),
                  const SizedBox(height: 28),
                  const Text('Địa chỉ máy chủ',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 15,
                          fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _address,
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    enableSuggestions: false,
                    maxLines: 1,
                    decoration: InputDecoration(
                      hintText: _mode == RiceAiServerMode.local
                          ? 'http://192.168.1.10:8015'
                          : 'https://may-chu.ts.net',
                      prefixIcon: const Icon(Icons.link_rounded, size: 21),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text('Chỉ nhập địa chỉ gốc, không thêm /docs.',
                      style: TextStyle(
                          color: AppTheme.textSecondary, fontSize: 12)),
                  if (_error != null) ...<Widget>[
                    const SizedBox(height: 14),
                    Text(_error!,
                        style: const TextStyle(
                            color: AppTheme.errorRed, fontSize: 13)),
                  ],
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 14),
              decoration: const BoxDecoration(
                color: AppTheme.cardSolid,
                border: Border(top: BorderSide(color: AppTheme.borderBeige)),
              ),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Kiểm tra và lưu'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ModeOption extends StatelessWidget {
  const _ModeOption({
    required this.icon,
    required this.title,
    required this.description,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
        selected: selected,
        button: true,
        child: Material(
          color: selected ? const Color(0xFFEAF0E7) : AppTheme.cardSolid,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(
                color: selected ? AppTheme.mossMid : AppTheme.borderBeige),
          ),
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: <Widget>[
                  Icon(icon, color: AppTheme.moss, size: 24),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(title,
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 3),
                        Text(description,
                            style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 12,
                                height: 1.35)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    selected
                        ? Icons.check_circle_rounded
                        : Icons.circle_outlined,
                    color: selected ? AppTheme.moss : AppTheme.textMuted,
                    size: 21,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
