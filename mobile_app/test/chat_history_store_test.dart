import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mobile_app/services/chat_history_store.dart';
import 'package:mobile_app/views/screens/ai_assistant_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('keeps account conversations separate on the same phone', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    const store = ChatHistoryStore();

    await store.save('account-a', <Map<String, dynamic>>[
      <String, dynamic>{'text': 'Câu hỏi của A', 'isUser': true},
    ]);
    expect(await store.load('account-b'), isEmpty);

    await store.save('account-b', <Map<String, dynamic>>[
      <String, dynamic>{'text': 'Câu hỏi của B', 'isUser': true},
    ]);
    expect((await store.load('account-a')).single['text'], 'Câu hỏi của A');
    expect((await store.load('account-b')).single['text'], 'Câu hỏi của B');
    expect(await store.load(null), isEmpty);
  });

  testWidgets('switching accounts replaces the visible conversation',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    const store = ChatHistoryStore();
    await store.save('account-a', <Map<String, dynamic>>[
      <String, dynamic>{'text': 'Câu hỏi riêng A', 'isUser': true},
    ]);
    await store.save('account-b', <Map<String, dynamic>>[
      <String, dynamic>{'text': 'Câu hỏi riêng B', 'isUser': true},
    ]);

    Future<void> showAccount(String accountId) async {
      await tester.pumpWidget(MaterialApp(
        home: AiAssistantScreen(
          key: ValueKey<String>(accountId),
          accountId: accountId,
        ),
      ));
      await tester.pumpAndSettle();
    }

    await showAccount('account-a');
    expect(find.text('Câu hỏi riêng A'), findsOneWidget);
    expect(find.text('Câu hỏi riêng B'), findsNothing);

    await showAccount('account-b');
    expect(find.text('Câu hỏi riêng A'), findsNothing);
    expect(find.text('Câu hỏi riêng B'), findsOneWidget);

    await showAccount('account-a');
    expect(find.text('Câu hỏi riêng A'), findsOneWidget);
    expect(find.text('Câu hỏi riêng B'), findsNothing);
  });
}
