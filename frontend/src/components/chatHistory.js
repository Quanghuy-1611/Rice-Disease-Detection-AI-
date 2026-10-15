const greeting = {
  sender: 'bot',
  text: 'Chào bạn! Tôi là RiceAI - Chuyên gia Nông nghiệp. Bạn cần tư vấn gì về cây lúa hôm nay?',
};

const historyKey = (accountId) => `riceai_chat_history_v1_${accountId}`;

export function initialChatMessages(accountId) {
  if (!accountId) return [greeting];
  try {
    const stored = JSON.parse(localStorage.getItem(historyKey(accountId)) || '[]');
    if (!Array.isArray(stored)) return [greeting];
    const messages = stored.filter((message) =>
      (message?.sender === 'user' || message?.sender === 'bot') &&
      typeof message.text === 'string' && message.text.length > 0,
    );
    return [greeting, ...messages.slice(-100)];
  } catch {
    return [greeting];
  }
}

export function saveChatMessages(accountId, messages) {
  if (!accountId) return;
  try {
    localStorage.setItem(historyKey(accountId), JSON.stringify(messages.slice(1).slice(-100)));
  } catch {
    // Browsers may disable storage; the chat still works for this session.
  }
}
