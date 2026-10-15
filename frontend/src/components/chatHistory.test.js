import assert from 'node:assert/strict';
import test from 'node:test';

import { initialChatMessages, saveChatMessages } from './chatHistory.js';

test('switching accounts keeps each conversation private and restores its history', () => {
  const data = new Map();
  globalThis.localStorage = {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  };

  const greeting = initialChatMessages('account-a')[0];
  saveChatMessages('account-a', [greeting, { sender: 'user', text: 'Câu hỏi của A' }]);
  assert.equal(initialChatMessages('account-b').length, 1);

  saveChatMessages('account-b', [greeting, { sender: 'user', text: 'Câu hỏi của B' }]);
  assert.deepEqual(initialChatMessages('account-a').map((message) => message.text),
    [greeting.text, 'Câu hỏi của A']);
  assert.deepEqual(initialChatMessages('account-b').map((message) => message.text),
    [greeting.text, 'Câu hỏi của B']);
  assert.equal(initialChatMessages(null).length, 1);
});
