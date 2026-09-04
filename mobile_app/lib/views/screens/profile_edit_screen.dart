import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../services/auth_service.dart';

class ProfileEditScreen extends StatefulWidget {
  const ProfileEditScreen({super.key, required this.initialName});
  final String initialName;

  @override
  State<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends State<ProfileEditScreen> {
  late final TextEditingController _nameController;
  String? _error;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialName);
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await context
          .read<AuthService>()
          .updateProfile(fullName: _nameController.text);
      if (mounted) Navigator.of(context).pop(true);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppTheme.porcelain,
        appBar: AppBar(title: const Text('Chỉnh sửa hồ sơ')),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Text('Tên hiển thị',
                      style:
                          TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _nameController,
                    maxLength: 80,
                    textCapitalization: TextCapitalization.words,
                    decoration:
                        const InputDecoration(hintText: 'Ví dụ: Nguyễn Văn A'),
                  ),
                  if (_error != null)
                    Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(_error!,
                            style: const TextStyle(color: AppTheme.dangerRed))),
                  const SizedBox(height: 8),
                  const Text(
                      'Số điện thoại được xác thực bằng OTP nên không chỉnh sửa ở đây.',
                      style: TextStyle(
                          color: AppTheme.textSecondary, height: 1.4)),
                  const Spacer(),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _saving ? null : _save,
                      child: _saving
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : const Text('Lưu thay đổi'),
                    ),
                  ),
                ]),
          ),
        ),
      );
}
