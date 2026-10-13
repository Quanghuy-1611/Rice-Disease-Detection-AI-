import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/errors/api_exception.dart';
import '../../core/theme/app_theme.dart';
import '../../services/prediction_service.dart';

class PlanScreen extends StatefulWidget {
  const PlanScreen({super.key});

  @override
  State<PlanScreen> createState() => _PlanScreenState();
}

class _PlanScreenState extends State<PlanScreen> {
  final PredictionService _service = PredictionService();
  Map<String, dynamic>? _plan;
  Map<String, dynamic>? _catalog;
  bool _loading = true;
  bool _busy = false;
  String? _error;
  String? _notice;

  Future<void> _load() async {
    try {
      final results = await Future.wait<
          Map<String, dynamic>>(<Future<Map<String, dynamic>>>[
        _service.getPlan(),
        _service.getPlanCatalog(),
      ]);
      if (!mounted) return;
      setState(() {
        _plan = results[0];
        _catalog = results[1];
        _loading = false;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error is ApiException
            ? error.message
            : 'Chưa tải được thông tin gói. Hãy kiểm tra máy chủ và thử lại.';
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _startTrial() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await _service.startPlusTrial();
      await _load();
      if (!mounted) return;
      setState(() => _notice = 'Plus dùng thử đã được kích hoạt.');
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Đã bật Plus dùng thử'),
          content: const Text(
              'Bạn được dùng thử Plus trong 1 tháng. Hãy đóng hẳn RiceAI rồi mở lại để chuyển sang giao diện Plus.'),
          actions: <Widget>[
            FilledButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('Đã hiểu')),
          ],
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error is ApiException
          ? error.message
          : 'Chưa bật được dùng thử Plus.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _requestPayment() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await _service.requestPlusPayment();
      await _load();
      if (!mounted) return;
      setState(
          () => _notice = 'Đã tạo mã chuyển khoản. Xem thông tin bên dưới.');
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error is ApiException
          ? error.message
          : 'Chưa tạo được yêu cầu thanh toán.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _copy(String value) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Đã sao chép.')),
    );
  }

  String _date(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? '')?.toLocal();
    if (parsed == null) return '—';
    return '${parsed.day.toString().padLeft(2, '0')}/${parsed.month.toString().padLeft(2, '0')}/${parsed.year}';
  }

  String _money(dynamic value) {
    final raw =
        (value is num ? value.toInt() : int.tryParse('$value') ?? 0).toString();
    final buffer = StringBuffer();
    for (var i = 0; i < raw.length; i++) {
      if (i > 0 && (raw.length - i) % 3 == 0) buffer.write('.');
      buffer.write(raw[i]);
    }
    return '$bufferđ';
  }

  BoxDecoration _panel({Color color = AppTheme.cardSolid}) => BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.borderBeige),
      );

  @override
  Widget build(BuildContext context) {
    final plan = _plan;
    final catalog = _catalog;
    final isPlus = plan?['plan'] == 'plus';
    final unlimited = plan?['unlimited'] == true;
    final trial = plan?['trial_active'] == true;
    final pending = plan?['pending_request'] is Map
        ? Map<String, dynamic>.from(plan!['pending_request'] as Map)
        : null;
    final bank = catalog?['payment_bank'] is Map
        ? Map<String, dynamic>.from(catalog!['payment_bank'] as Map)
        : null;

    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        title: const Text('Gói sử dụng'),
        actions: <Widget>[
          IconButton(
            tooltip: 'Cập nhật trạng thái gói',
            onPressed: _busy ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null && plan == null
              ? Center(
                  child: Padding(
                  padding: const EdgeInsets.all(24),
                  child:
                      Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                    Text(_error!, textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    FilledButton(
                        onPressed: _load, child: const Text('Thử lại')),
                  ]),
                ))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(20, 10, 20, 36),
                    children: <Widget>[
                      _CurrentPlanCard(
                        isPlus: isPlus,
                        unlimited: unlimited,
                        trial: trial,
                        remaining: plan?['remaining'],
                        validUntil: plan?['valid_until'] == null
                            ? null
                            : _date(plan!['valid_until']),
                      ),
                      const SizedBox(height: 24),
                      if (_error != null) _StatusMessage(_error!, error: true),
                      if (_notice != null) _StatusMessage(_notice!),
                      if (_error != null || _notice != null)
                        const SizedBox(height: 18),
                      Text(isPlus ? 'Quyền lợi Plus' : 'Nâng cấp Plus',
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(
                                  fontWeight: FontWeight.w800,
                                  color: AppTheme.textPrimary)),
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.all(21),
                        decoration: _panel(),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              const Text('Phân tích nhiều ảnh trong một lượt',
                                  style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.w800,
                                      color: AppTheme.textPrimary)),
                              const SizedBox(height: 7),
                              const Text('Tối đa 5 ảnh · 80 lượt mỗi tháng',
                                  style: TextStyle(
                                      fontSize: 14,
                                      color: AppTheme.textSecondary)),
                              const SizedBox(height: 18),
                              const _Benefit('Đối chiếu kết quả từ nhiều ảnh'),
                              const _Benefit('Hiển thị vùng mô hình chú ý'),
                              const _Benefit(
                                  'Cảnh báo ảnh chưa đủ rõ hoặc kết quả chưa thống nhất'),
                              const SizedBox(height: 18),
                              Container(height: 1, color: AppTheme.borderBeige),
                              const SizedBox(height: 17),
                              if (unlimited)
                                const Text(
                                    'Tài khoản nhân sự dùng không giới hạn.',
                                    style: TextStyle(
                                        color: AppTheme.textSecondary))
                              else if (trial)
                                Text(
                                    'Dùng thử đến ${_date(plan?['trial_valid_until'])}. Sau đó có thể gia hạn bằng chuyển khoản.',
                                    style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        height: 1.45))
                              else if (isPlus)
                                Text(
                                    'Plus có hiệu lực đến ${_date(plan?['valid_until'])}.',
                                    style: const TextStyle(
                                        color: AppTheme.textSecondary))
                              else
                                Text(
                                    'Dùng thử 1 tháng miễn phí. Sau đó ${_money(catalog?['plus']?['intro_price_vnd'])} cho tháng trả phí đầu tiên.',
                                    style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        height: 1.45)),
                              const SizedBox(height: 16),
                              if (catalog?['plus_ready'] != true)
                                const Text(
                                    'Plus đang được kiểm định và chưa mở đăng ký.',
                                    style: TextStyle(
                                        color: AppTheme.textSecondary))
                              else if (plan?['trial_available'] == true)
                                SizedBox(
                                    width: double.infinity,
                                    child: FilledButton(
                                      onPressed: _busy ? null : _startTrial,
                                      child: Text(_busy
                                          ? 'Đang xử lý...'
                                          : 'Dùng thử Plus 1 tháng'),
                                    ))
                              else if (!unlimited &&
                                  pending == null &&
                                  (!isPlus || trial))
                                SizedBox(
                                    width: double.infinity,
                                    child: FilledButton(
                                      onPressed: _busy ? null : _requestPayment,
                                      child: Text(_busy
                                          ? 'Đang xử lý...'
                                          : trial
                                              ? 'Gia hạn sau dùng thử'
                                              : 'Nâng cấp Plus'),
                                    ))
                              else if (pending != null)
                                const Text(
                                    'Đang chờ Admin xác nhận chuyển khoản.',
                                    style: TextStyle(
                                        color: AppTheme.moss,
                                        fontWeight: FontWeight.w700)),
                            ]),
                      ),
                      if (pending != null && bank != null) ...<Widget>[
                        const SizedBox(height: 22),
                        _PaymentCard(
                          bank: bank,
                          pending: pending,
                          money: _money,
                          onCopy: _copy,
                        ),
                      ],
                      const SizedBox(height: 24),
                      const Text(
                          'Gói được lưu theo tài khoản. Sau khi bật dùng thử hoặc được Admin duyệt, hãy đóng hẳn rồi mở lại RiceAI để chuyển giao diện.',
                          style: TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 13,
                              height: 1.5)),
                    ],
                  ),
                ),
    );
  }
}

class _CurrentPlanCard extends StatelessWidget {
  const _CurrentPlanCard(
      {required this.isPlus,
      required this.unlimited,
      required this.trial,
      required this.remaining,
      required this.validUntil});

  final bool isPlus;
  final bool unlimited;
  final bool trial;
  final dynamic remaining;
  final String? validUntil;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
            color: AppTheme.moss, borderRadius: BorderRadius.circular(22)),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('GÓI HIỆN TẠI',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: .7),
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.3)),
              const SizedBox(height: 8),
              Text(isPlus ? 'RiceAI Plus' : 'RiceAI Basic',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 27,
                      fontWeight: FontWeight.w800)),
              const SizedBox(height: 5),
              Text(
                  unlimited
                      ? 'Dùng không giới hạn'
                      : trial
                          ? 'Đang dùng thử miễn phí'
                          : isPlus
                              ? 'Đã kích hoạt'
                              : 'Miễn phí',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: .83),
                      fontSize: 14)),
              const SizedBox(height: 20),
              Divider(color: Colors.white.withValues(alpha: .2), height: 1),
              const SizedBox(height: 16),
              Row(children: <Widget>[
                Expanded(
                    child: _PlanDetail('Lượt còn lại',
                        unlimited ? 'Không giới hạn' : '$remaining')),
                if (validUntil != null)
                  Expanded(child: _PlanDetail('Hiệu lực đến', validUntil!)),
              ]),
            ]),
      );
}

class _PlanDetail extends StatelessWidget {
  const _PlanDetail(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) =>
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Text(label,
            style: TextStyle(
                color: Colors.white.withValues(alpha: .66), fontSize: 12)),
        const SizedBox(height: 5),
        Text(value,
            style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 17)),
      ]);
}

class _Benefit extends StatelessWidget {
  const _Benefit(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Icon(Icons.check_circle_outline_rounded,
                  color: AppTheme.mossMid, size: 19),
              const SizedBox(width: 10),
              Expanded(
                  child: Text(text,
                      style: const TextStyle(
                          color: AppTheme.textPrimary, fontSize: 14))),
            ]),
      );
}

class _StatusMessage extends StatelessWidget {
  const _StatusMessage(this.message, {this.error = false});
  final String message;
  final bool error;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
            color: error ? const Color(0xFFFFEFED) : const Color(0xFFEAF3E7),
            borderRadius: BorderRadius.circular(12)),
        child: Text(message,
            style: TextStyle(color: error ? AppTheme.errorRed : AppTheme.moss)),
      );
}

class _PaymentCard extends StatelessWidget {
  const _PaymentCard(
      {required this.bank,
      required this.pending,
      required this.money,
      required this.onCopy});
  final Map<String, dynamic> bank;
  final Map<String, dynamic> pending;
  final String Function(dynamic) money;
  final Future<void> Function(String) onCopy;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: AppTheme.cardSolid,
            border: Border.all(color: AppTheme.borderBeige),
            borderRadius: BorderRadius.circular(20)),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('Chuyển khoản Plus',
                  style: TextStyle(
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary)),
              const SizedBox(height: 7),
              const Text(
                  'Quét QR hoặc dùng thông tin bên dưới. QR chưa điền sẵn số tiền và nội dung.',
                  style: TextStyle(color: AppTheme.textSecondary, height: 1.4)),
              const SizedBox(height: 18),
              Center(
                  child: SizedBox(
                width: 252,
                height: 252,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Stack(clipBehavior: Clip.hardEdge, children: <Widget>[
                    Positioned(
                        left: -146,
                        top: -350,
                        width: 580,
                        child:
                            Image.asset('assets/payment/riceai-bank-qr.png')),
                  ]),
                ),
              )),
              const SizedBox(height: 18),
              const _PaymentLine('Ngân hàng', 'Techcombank'),
              _PaymentLine('Người nhận', '${bank['account_name']}'),
              _PaymentLine('Số tài khoản', '${bank['account_number']}',
                  onCopy: () => onCopy('${bank['account_number']}')),
              _PaymentLine('Số tiền', money(pending['price_vnd'])),
              _PaymentLine('Nội dung', '${pending['payment_code']}',
                  onCopy: () => onCopy('${pending['payment_code']}')),
              const SizedBox(height: 15),
              const Text(
                  'Chỉ chuyển tiền khi tên người nhận trong ứng dụng ngân hàng khớp. Admin kiểm tra tiền đã vào rồi mới kích hoạt Plus; không cần gửi ảnh biên lai để tự duyệt.',
                  style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 13,
                      height: 1.45)),
            ]),
      );
}

class _PaymentLine extends StatelessWidget {
  const _PaymentLine(this.label, this.value, {this.onCopy});
  final String label;
  final String value;
  final VoidCallback? onCopy;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(children: <Widget>[
          SizedBox(
              width: 88,
              child: Text(label,
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 13))),
          Expanded(
              child: Text(value,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 13,
                      fontWeight: FontWeight.w700))),
          if (onCopy != null)
            IconButton(
              tooltip: 'Sao chép $label',
              onPressed: onCopy,
              icon: const Icon(Icons.copy_rounded, size: 17),
              visualDensity: VisualDensity.compact,
            ),
        ]),
      );
}
