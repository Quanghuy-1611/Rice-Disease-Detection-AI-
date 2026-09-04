import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';
import '../views/widgets/app_card.dart';

class PrivacyScreen extends StatelessWidget {
  const PrivacyScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppTheme.porcelain,
        appBar: AppBar(title: const Text('Quyền riêng tư')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: const <Widget>[
            _PrivacySection(
              icon: Icons.photo_camera_outlined,
              title: 'Ảnh lá lúa',
              content:
                  'Ảnh bạn chọn hoặc chụp được gửi tới máy chủ RiceAI để phân tích. Ảnh không được dùng làm dữ liệu nghiên cứu hay huấn luyện lại nếu chưa có sự đồng ý riêng của bạn.',
            ),
            _PrivacySection(
              icon: Icons.phone_android_outlined,
              title: 'Tài khoản',
              content:
                  'Số điện thoại chỉ dùng để xác thực OTP. RiceAI không hiển thị số này công khai cho người dùng khác.',
            ),
            _PrivacySection(
              icon: Icons.storage_outlined,
              title: 'Dữ liệu trên thiết bị',
              content:
                  'Thông báo trong ứng dụng và tệp tạm có thể được xóa tại Hồ sơ. Đăng xuất xóa phiên đăng nhập khỏi thiết bị.',
            ),
            _PrivacySection(
              icon: Icons.info_outline_rounded,
              title: 'Lưu ý chuyên môn',
              content:
                  'Kết quả AI và nội dung trợ lý là thông tin hỗ trợ. Hãy đối chiếu thực tế ruộng và tư vấn cán bộ chuyên môn trước khi dùng biện pháp xử lý.',
            ),
          ],
        ),
      );
}

class _PrivacySection extends StatelessWidget {
  const _PrivacySection(
      {required this.icon, required this.title, required this.content});
  final IconData icon;
  final String title;
  final String content;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: AppCard(
          child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Icon(icon, color: AppTheme.moss),
                const SizedBox(width: 12),
                Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                      Text(title,
                          style: const TextStyle(fontWeight: FontWeight.w900)),
                      const SizedBox(height: 6),
                      Text(content,
                          style: const TextStyle(
                              color: AppTheme.textSecondary, height: 1.45)),
                    ])),
              ]),
        ),
      );
}
