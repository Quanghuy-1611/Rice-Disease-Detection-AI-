import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/auth_service.dart';

/// Ba lối vào không phụ thuộc SMS: email thật có xác minh, Google và khách.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isRegistering = false;
  bool _obscurePassword = true;
  String _errorMessage = '';

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _showError(String message) {
    if (mounted) setState(() => _errorMessage = message);
  }

  void _finish() {
    if (mounted) Navigator.of(context).pop();
  }

  Future<void> _submitEmail() async {
    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    if (email.isEmpty || !email.contains('@')) {
      _showError('Vui lòng nhập địa chỉ email hợp lệ.');
      return;
    }
    if (password.length < 6) {
      _showError('Mật khẩu cần có ít nhất 6 ký tự.');
      return;
    }
    if (_isRegistering && name.length < 2) {
      _showError('Vui lòng nhập họ tên.');
      return;
    }
    setState(() => _errorMessage = '');
    final auth = context.read<AuthService>();
    if (_isRegistering) {
      await auth.registerWithEmail(
        fullName: name,
        email: email,
        password: password,
        onError: _showError,
        onVerificationSent: () {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Đã gửi liên kết xác minh tới $email.'),
              duration: const Duration(seconds: 5),
            ),
          );
          setState(() {
            _isRegistering = false;
            _errorMessage =
                'Hãy xác minh email trước, sau đó đăng nhập bằng mật khẩu vừa tạo.';
          });
        },
      );
      return;
    }
    await auth.signInWithEmail(
      email: email,
      password: password,
      onError: _showError,
      onSuccess: _finish,
    );
  }

  Future<void> _signInGoogle() async {
    setState(() => _errorMessage = '');
    await context.read<AuthService>().signInWithGoogle(
          onError: _showError,
          onSuccess: _finish,
        );
  }

  Future<void> _tryGuest() async {
    setState(() => _errorMessage = '');
    await context.read<AuthService>().signInAsGuest(
          onError: _showError,
          onSuccess: _finish,
        );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final title = _isRegistering ? 'Tạo tài khoản' : 'Đăng nhập';
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 10, 24, 28),
          children: <Widget>[
            Text(title,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: AppTheme.textPrimary,
                      fontWeight: FontWeight.w900,
                    )),
            const SizedBox(height: 8),
            Text(
              _isRegistering
                  ? 'Dùng email thật. RiceAI sẽ gửi liên kết xác minh trước khi bạn có thể đăng nhập.'
                  : 'Đăng nhập để đồng bộ lịch sử quét và hồ sơ giữa các thiết bị.',
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 14, height: 1.45),
            ),
            const SizedBox(height: 28),
            if (_isRegistering) ...<Widget>[
              TextField(
                controller: _nameController,
                textCapitalization: TextCapitalization.words,
                decoration: _decoration('Họ và tên', Icons.person_outline_rounded),
              ),
              const SizedBox(height: 14),
            ],
            TextField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const <String>[AutofillHints.email],
              decoration: _decoration('Email', Icons.alternate_email_rounded),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              autofillHints: <String>[
                _isRegistering ? AutofillHints.newPassword : AutofillHints.password,
              ],
              decoration: _decoration('Mật khẩu', Icons.lock_outline_rounded).copyWith(
                suffixIcon: IconButton(
                  tooltip: _obscurePassword ? 'Hiện mật khẩu' : 'Ẩn mật khẩu',
                  icon: Icon(_obscurePassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined),
                  onPressed: () =>
                      setState(() => _obscurePassword = !_obscurePassword),
                ),
              ),
            ),
            if (_errorMessage.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              Text(_errorMessage,
                  style: const TextStyle(
                      color: AppTheme.errorRed, fontSize: 13, height: 1.35)),
            ],
            const SizedBox(height: 22),
            FilledButton(
              onPressed: auth.isLoading ? null : _submitEmail,
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16)),
              ),
              child: auth.isLoading
                  ? const SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2),
                    )
                  : Text(_isRegistering ? 'Tạo tài khoản' : 'Đăng nhập',
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 16)),
            ),
            TextButton(
              onPressed: auth.isLoading
                  ? null
                  : () => setState(() {
                        _isRegistering = !_isRegistering;
                        _errorMessage = '';
                      }),
              child: Text(_isRegistering
                  ? 'Đã có tài khoản? Đăng nhập'
                  : 'Chưa có tài khoản? Đăng ký'),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 10),
              child: Row(children: <Widget>[
                Expanded(child: Divider()),
                Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12),
                    child: Text('hoặc',
                        style: TextStyle(color: AppTheme.textMuted))),
                Expanded(child: Divider()),
              ]),
            ),
            OutlinedButton.icon(
              onPressed: auth.isLoading ? null : _signInGoogle,
              icon: const Icon(Icons.g_mobiledata_rounded, size: 30),
              label: const Text('Tiếp tục với Google',
                  style: TextStyle(fontWeight: FontWeight.w800)),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(54),
                foregroundColor: AppTheme.textPrimary,
                side: const BorderSide(color: AppTheme.moss),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16)),
              ),
            ),
            const SizedBox(height: 10),
            TextButton.icon(
              onPressed: auth.isLoading ? null : _tryGuest,
              icon: const Icon(Icons.explore_outlined),
              label: const Text('Dùng thử không cần tài khoản'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Chế độ dùng thử không dùng email và dữ liệu không gắn với một tài khoản cá nhân.',
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: AppTheme.textMuted, fontSize: 11, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }

  InputDecoration _decoration(String label, IconData icon) => InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
        filled: true,
        fillColor: Colors.white,
      );
}
