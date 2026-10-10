import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/auth_service.dart';

/// Đăng nhập email đã xác minh, cùng luồng đăng ký như trên web.
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
  String _noticeMessage = '';

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _showError(String message) {
    if (mounted) {
      setState(() {
        _errorMessage = message;
        _noticeMessage = '';
      });
    }
  }

  void _finish() {
    if (mounted) Navigator.of(context).pop(true);
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
    setState(() {
      _errorMessage = '';
      _noticeMessage = '';
    });
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
            _noticeMessage =
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

  Future<void> _resetPassword() async {
    final email = _emailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      _showError('Nhập email hợp lệ trước khi đặt lại mật khẩu.');
      return;
    }
    setState(() {
      _errorMessage = '';
      _noticeMessage = '';
    });
    await context.read<AuthService>().sendPasswordReset(
          email: email,
          onError: _showError,
          onSent: () {
            if (mounted) {
              setState(() => _noticeMessage =
                  'Nếu email đã có tài khoản, bạn sẽ nhận được thư đặt lại mật khẩu.');
            }
          },
        );
  }

  Future<void> _resendVerification() async {
    final email = _emailController.text.trim();
    if (email.isEmpty ||
        !email.contains('@') ||
        _passwordController.text.isEmpty) {
      _showError('Nhập email và mật khẩu để gửi lại thư xác minh.');
      return;
    }
    setState(() {
      _errorMessage = '';
      _noticeMessage = '';
    });
    await context.read<AuthService>().resendVerificationEmail(
          email: email,
          password: _passwordController.text,
          onError: _showError,
          onFinished: (verified) {
            if (mounted) {
              setState(() => _noticeMessage = verified
                  ? 'Email đã được xác minh. Bạn có thể đăng nhập.'
                  : 'Đã gửi lại thư xác minh. Hãy kiểm tra hộp thư và mục spam.');
            }
          },
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
            Center(
              child: Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: AppTheme.moss,
                  borderRadius: BorderRadius.circular(22),
                ),
                child: const Icon(Icons.mail_outline_rounded,
                    color: Colors.white, size: 38),
              ),
            ),
            const SizedBox(height: 20),
            Text(title,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: AppTheme.textPrimary,
                      fontWeight: FontWeight.w900,
                    )),
            const SizedBox(height: 8),
            Text(
              _isRegistering
                  ? 'Dùng email thật. RiceAI sẽ gửi liên kết xác minh trước khi bạn có thể đăng nhập.'
                  : 'Dùng email đã xác minh để lưu lịch sử chẩn đoán của bạn.',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 14, height: 1.45),
            ),
            const SizedBox(height: 28),
            if (_isRegistering) ...<Widget>[
              TextField(
                controller: _nameController,
                textCapitalization: TextCapitalization.words,
                decoration:
                    _decoration('Họ và tên', Icons.person_outline_rounded),
              ),
              const SizedBox(height: 14),
            ],
            TextField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              autocorrect: false,
              enableSuggestions: false,
              autofillHints: const <String>[AutofillHints.email],
              decoration: _decoration('Email', Icons.mail_outline_rounded),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) {
                if (!auth.isLoading) _submitEmail();
              },
              autofillHints: <String>[
                _isRegistering
                    ? AutofillHints.newPassword
                    : AutofillHints.password,
              ],
              decoration:
                  _decoration('Mật khẩu', Icons.lock_outline_rounded).copyWith(
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
              _AuthMessage(message: _errorMessage, isError: true),
            ],
            if (_noticeMessage.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              _AuthMessage(message: _noticeMessage, isError: false),
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
            if (!_isRegistering)
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                spacing: 8,
                children: <Widget>[
                  TextButton(
                    onPressed: auth.isLoading ? null : _resetPassword,
                    child: const Text('Quên mật khẩu?'),
                  ),
                  TextButton(
                    onPressed: auth.isLoading ? null : _resendVerification,
                    child: const Text('Gửi lại thư xác minh'),
                  ),
                ],
              ),
            TextButton(
              onPressed: auth.isLoading
                  ? null
                  : () => setState(() {
                        _isRegistering = !_isRegistering;
                        _errorMessage = '';
                        _noticeMessage = '';
                      }),
              child: Text(_isRegistering
                  ? 'Đã có tài khoản? Đăng nhập'
                  : 'Chưa có tài khoản? Đăng ký ngay'),
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

class _AuthMessage extends StatelessWidget {
  const _AuthMessage({required this.message, required this.isError});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final color = isError ? AppTheme.errorRed : AppTheme.moss;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isError ? const Color(0xFFFEF2F2) : const Color(0xFFF0FDF4),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.16)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(
            isError
                ? Icons.error_outline_rounded
                : Icons.mark_email_read_outlined,
            color: color,
            size: 18,
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: color, fontSize: 13, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}
