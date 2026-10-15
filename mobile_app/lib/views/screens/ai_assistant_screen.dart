import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../core/theme/app_theme.dart';
import '../../services/ai_assistant_service.dart';
import '../../services/chat_history_store.dart';

const String _greeting =
    'Chào bạn! Tôi có thể giải thích triệu chứng, cách phòng ngừa và xử lý bệnh lúa. Kết quả chỉ mang tính hỗ trợ, không thay thế tư vấn cán bộ nông nghiệp.';

class _ChatMessage {
  const _ChatMessage({
    required this.text,
    required this.isUser,
    this.sources = const <String>[],
  });

  final String text;
  final bool isUser;
  final List<String> sources;
}

class AiAssistantScreen extends StatefulWidget {
  const AiAssistantScreen({super.key, this.accountId});

  final String? accountId;

  @override
  State<AiAssistantScreen> createState() => _AiAssistantScreenState();
}

class _AiAssistantScreenState extends State<AiAssistantScreen> {
  final AiAssistantService _aiService = AiAssistantService();
  final ChatHistoryStore _historyStore = const ChatHistoryStore();
  final TextEditingController _textController = TextEditingController();
  final List<_ChatMessage> _messages = <_ChatMessage>[
    const _ChatMessage(
      text: _greeting,
      isUser: false,
    ),
  ];
  bool _isLoading = false;
  bool _historyLoaded = false;
  Future<void> _saveQueue = Future<void>.value();

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    List<Map<String, dynamic>> stored;
    try {
      stored = await _historyStore.load(widget.accountId);
    } catch (_) {
      stored = <Map<String, dynamic>>[];
    }
    if (!mounted) return;
    setState(() {
      _messages.insertAll(
        0,
        stored.map((item) => _ChatMessage(
              text: item['text'] as String,
              isUser: item['isUser'] as bool,
              sources: (item['sources'] is List)
                  ? (item['sources'] as List).whereType<String>().toList()
                  : const <String>[],
            )),
      );
      _historyLoaded = true;
    });
  }

  void _saveHistory() {
    final snapshot = _messages
        .take(100)
        .map((message) => <String, dynamic>{
              'text': message.text,
              'isUser': message.isUser,
              'sources': message.sources,
            })
        .toList();
    // The last item is the static greeting, not an account message.
    if (snapshot.isNotEmpty &&
        snapshot.last['isUser'] == false &&
        snapshot.last['text'] == _greeting) {
      snapshot.removeLast();
    }
    _saveQueue = _saveQueue.then((_) async {
      try {
        await _historyStore.save(widget.accountId, snapshot);
      } catch (_) {
        // The current conversation remains usable if local storage is full.
      }
    });
  }

  Future<void> _sendMessage() async {
    final message = _textController.text.trim();
    if (message.isEmpty || _isLoading || !_historyLoaded) return;

    setState(() {
      _messages.insert(0, _ChatMessage(text: message, isUser: true));
      _isLoading = true;
    });
    _saveHistory();
    _textController.clear();

    try {
      final response = await _aiService.askQuestion(message);
      final rawSources = response['sources'];
      final sources = rawSources is List
          ? rawSources
              .map((item) => item.toString())
              .where((item) => item.isNotEmpty)
              .toList()
          : <String>[];
      if (!mounted) return;
      setState(() {
        _messages.insert(
          0,
          _ChatMessage(
            text: response['reply'] as String,
            isUser: false,
            sources: sources,
          ),
        );
      });
      _saveHistory();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _messages.insert(
          0,
          _ChatMessage(
            text:
                'Chưa thể kết nối trợ lý. Kiểm tra máy chủ và thử lại.\n$error',
            isUser: false,
          ),
        );
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.porcelain,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.smart_toy_outlined, color: AppTheme.moss),
            SizedBox(width: 8),
            Text('Trợ lý RiceAI'),
          ],
        ),
      ),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Expanded(
              child: ListView.builder(
                reverse: true,
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                itemCount: _messages.length,
                itemBuilder: (context, index) =>
                    _ChatBubble(message: _messages[index])
                        .animate()
                        .fade(duration: 220.ms),
              ),
            ),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.only(left: 20, bottom: 8),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      SizedBox(
                        height: 14,
                        width: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: 8),
                      Text('RiceAI đang trả lời...',
                          style: TextStyle(color: AppTheme.textSecondary)),
                    ],
                  ),
                ),
              ),
            _buildComposer(),
          ],
        ),
      ),
    );
  }

  Widget _buildComposer() => SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
          child: Row(
            children: <Widget>[
              Expanded(
                child: TextField(
                  controller: _textController,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _sendMessage(),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: dấu hiệu bệnh đạo ôn?',
                    filled: true,
                    fillColor: AppTheme.cardSolid,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(18),
                      borderSide: const BorderSide(color: AppTheme.borderBeige),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              FilledButton(
                onPressed: _isLoading || !_historyLoaded ? null : _sendMessage,
                style: FilledButton.styleFrom(
                    shape: const CircleBorder(),
                    padding: const EdgeInsets.all(15)),
                child: const Icon(Icons.send_rounded),
              ),
            ],
          ),
        ),
      );
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.message});
  final _ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final foreground = message.isUser ? Colors.white : AppTheme.textPrimary;
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints:
            BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .82),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: message.isUser ? AppTheme.moss : AppTheme.cardSolid,
          borderRadius: BorderRadius.circular(18),
          border:
              message.isUser ? null : Border.all(color: AppTheme.borderBeige),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(message.text,
                style: TextStyle(color: foreground, height: 1.45)),
            if (message.sources.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              Text('Nguồn: ${message.sources.join(' • ')}',
                  style: TextStyle(
                      color: foreground.withValues(alpha: .72), fontSize: 11)),
            ],
          ],
        ),
      ),
    );
  }
}
