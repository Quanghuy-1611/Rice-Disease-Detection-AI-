import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './Chatbot.css';

function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Chào bạn! Tôi là RiceAI - Chuyên gia Nông nghiệp. Bạn cần tư vấn gì về cây lúa hôm nay?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    const handleOpenChat = (e) => {
      setIsOpen(true);
      if (e.detail) {
        // Tự động set input và gửi
        const userMessage = e.detail;
        setMessages(prev => [...prev, { sender: 'user', text: userMessage }]);
        setIsTyping(true);
        axios.post('/api/chat/ask', { message: userMessage })
          .then(res => setMessages(prev => [...prev, { sender: 'bot', text: res.data.reply }]))
          .catch(err => {
            const detail = err.response?.data?.detail || 'Xin lỗi, tôi đang bận. Vui lòng thử lại sau.';
            setMessages(prev => [...prev, { sender: 'bot', text: detail }]);
          })
          .finally(() => setIsTyping(false));
      }
    };

    window.addEventListener('open-chat', handleOpenChat);
    return () => window.removeEventListener('open-chat', handleOpenChat);
  }, []);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, { sender: 'user', text: userMessage }]);
    setInput('');
    setIsTyping(true);

    try {
      const res = await axios.post('/api/chat/ask', { message: userMessage });
      setMessages(prev => [...prev, { sender: 'bot', text: res.data.reply }]);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Xin lỗi, tôi đang bận hoặc mất kết nối. Vui lòng thử lại sau.';
      setMessages(prev => [...prev, { sender: 'bot', text: detail }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button 
        className={`chatbot-toggle ${isOpen ? 'hidden' : ''}`}
        onClick={() => setIsOpen(true)}
      >
        💬 Trợ Lý AI
      </button>

      {/* Chat Window */}
      <div className={`chatbot-window ${isOpen ? 'open' : ''}`}>
        <div className="chatbot-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.5rem' }}>👨‍🌾</span>
            <div>
              <h3 style={{ fontSize: '1rem', margin: 0, color: 'white' }}>Chuyên gia RiceAI</h3>
              <p style={{ fontSize: '0.8rem', margin: 0, color: '#a7f3d0' }}>Luôn sẵn sàng hỗ trợ</p>
            </div>
          </div>
          <button className="chatbot-close" onClick={() => setIsOpen(false)}>×</button>
        </div>

        <div className="chatbot-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-bubble ${msg.sender === 'user' ? 'user' : 'bot'}`}>
              <div className="message-content">
                {msg.sender === 'bot' ? (
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                ) : (
                  msg.text
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="message-bubble bot typing">
              <span>.</span><span>.</span><span>.</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chatbot-input-area" onSubmit={handleSend}>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập câu hỏi của bạn..." 
            className="chatbot-input"
          />
          <button type="submit" className="chatbot-send-btn" disabled={!input.trim() || isTyping}>
            ➤
          </button>
        </form>
      </div>
    </>
  );
}

export default Chatbot;
