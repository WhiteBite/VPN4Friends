import React, { useState, useEffect, useCallback, useRef } from 'react';
import { fetchAdminChats, fetchChatHistory, sendChatReply, fetchUsers } from '../api';
import Card from '../ui/Card';
import Button from '../ui/Button';

export default function AdminChats({ onError, initialUser, onInitialUserProcessed }) {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // View states: null = list viewing, number = viewing specific user_id
  const [activeChatUserId, setActiveChatUserId] = useState(null);
  const [activeChatUser, setActiveChatUser] = useState(null); // the user object
  
  // New Chat Selection State
  const [isSelectingUser, setIsSelectingUser] = useState(false);
  const [allUsers, setAllUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [userSearch, setUserSearch] = useState('');

  // Thread state
  const [messages, setMessages] = useState([]);
  const [loadingThread, setLoadingThread] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef(null);

  const isDev = import.meta.env.DEV;

  const loadChats = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchAdminChats();
      setChats(data || []);
    } catch (err) {
      if (isDev) {
        setChats([
          { user_id: 1, full_name: 'Вася П', last_message: 'У меня не работает!', is_last_from_admin: false, last_message_at: new Date().toISOString() },
          { user_id: 2, full_name: 'Анна', last_message: 'Попробуй перезагрузить', is_last_from_admin: true, last_message_at: new Date(Date.now() - 3600000).toISOString() }
        ]);
      } else {
        onError(err.message || 'Ошибка загрузки чатов');
      }
    } finally {
      setLoading(false);
    }
  }, [isDev, onError]);

  const loadAllUsers = async () => {
    try {
      setLoadingUsers(true);
      const data = await fetchUsers();
      setAllUsers(data || []);
    } catch (err) {
      onError(err.message || 'Ошибка загрузки пользователей');
    } finally {
      setLoadingUsers(false);
    }
  };

  const openChatThread = useCallback(async (chat) => {
    setActiveChatUserId(chat.user_id || chat.id); // support both chat list and user list objects
    setActiveChatUser(chat);
    setLoadingThread(true);
    setIsSelectingUser(false);
    try {
      if (isDev) {
        setMessages([
          { id: 1, is_from_admin: false, text: 'Привет! Не работает VPN.', created_at: new Date().toISOString() },
          { id: 2, is_from_admin: true, text: 'Привет, попробуй обновить конфиг.', created_at: new Date().toISOString() }
        ]);
      } else {
        const data = await fetchChatHistory(chat.user_id || chat.id);
        setMessages(data || []);
      }
    } catch (err) {
      // If history fails, we might still want to allow sending a new message
      setMessages([]);
      console.error('History fetch failed:', err);
    } finally {
      setLoadingThread(false);
    }
  }, [isDev]);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Handle incoming focus request
  useEffect(() => {
    if (initialUser) {
      openChatThread(initialUser);
      if (onInitialUserProcessed) onInitialUserProcessed();
    }
  }, [initialUser, openChatThread, onInitialUserProcessed]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSendReply = async () => {
    if (!replyText.trim()) return;
    setSending(true);
    try {
      if (!isDev) {
        const newMsg = await sendChatReply(activeChatUserId, replyText);
        setMessages(prev => [...prev, newMsg]);
      } else {
        setMessages(prev => [...prev, { id: Date.now(), is_from_admin: true, text: replyText, created_at: new Date().toISOString()}]);
      }
      setReplyText('');
      // Refresh list in background
      loadChats();
    } catch (err) {
      onError(err.message || 'Ошибка отправки');
    } finally {
      setSending(false);
    }
  };

  const filteredUsers = allUsers.filter(u => {
    const search = userSearch.toLowerCase();
    return (
      (u.full_name || '').toLowerCase().includes(search) || 
      (u.username || '').toLowerCase().includes(search) ||
      (u.telegram_id || '').toString().includes(search)
    );
  });

  // Render User Selection View
  if (isSelectingUser) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <Button variant="secondary" onClick={() => setIsSelectingUser(false)} style={{ padding: '8px 12px' }}>Назад</Button>
          <div style={{ fontWeight: 'bold', fontSize: '18px' }}>Начать новый чат</div>
        </div>
        
        <input 
          type="text"
          placeholder="Поиск по имени или @username..."
          value={userSearch}
          onChange={(e) => setUserSearch(e.target.value)}
          style={{
            padding: '12px',
            borderRadius: '12px',
            border: '1px solid var(--border)',
            background: 'var(--bg-elevated)',
            color: 'var(--text)',
            fontSize: '15px',
            outline: 'none'
          }}
        />

        {loadingUsers ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>Загрузка пользователей...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '60vh', overflowY: 'auto' }}>
            {filteredUsers.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>Никого не нашли</div>
            ) : (
              filteredUsers.map(u => (
                <div 
                  key={u.id}
                  onClick={() => openChatThread({ ...u, user_id: u.id })}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '10px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                >
                  <span style={{ fontWeight: 'bold' }}>{u.full_name}</span>
                  <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    {u.username ? `@${u.username}` : `ID: ${u.telegram_id}`}
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    );
  }

  // Render Thread List View
  if (!activeChatUserId) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <Button 
          variant="primary" 
          onClick={() => {
            setIsSelectingUser(true);
            loadAllUsers();
          }}
          style={{ marginBottom: '8px' }}
        >
          ➕ Написать пользователю
        </Button>

        {loading ? (
          <div className="empty-state">Загрузка чатов...</div>
        ) : chats.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <div className="empty-title">Нет активных чатов</div>
            <div className="empty-text">Нажмите кнопку выше, чтобы написать кому-то первым.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {chats.map(chat => (
              <div
                key={chat.user_id}
                onClick={() => openChatThread(chat)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '16px',
                  borderRadius: '12px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  cursor: 'pointer',
                  gap: '6px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'bold', fontSize: '16px', color: 'var(--text)' }}>
                    {chat.full_name} {chat.username && <span style={{color: 'var(--text-muted)', fontSize: '13px', fontWeight: 'normal'}}>@{chat.username}</span>}
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {new Date(chat.last_message_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                </div>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {chat.is_last_from_admin ? "Вы: " : ""}{chat.last_message}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Render Thread View
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '65vh', minHeight: '450px', backgroundColor: 'var(--bg-elevated)', borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden' }}>
      
      {/* Thread Header */}
      <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--surface)'}}>
        <div 
          onClick={() => setActiveChatUserId(null)} 
          style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--bg-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: '18px' }}
        >
          ⬅️
        </div>
        <div style={{ fontWeight: 'bold', fontSize: '16px' }}>{activeChatUser?.full_name}</div>
      </div>

      {/* Messages List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {loadingThread ? (
           <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '20px' }}>Загрузка истории...</div>
        ) : messages.length === 0 ? (
           <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '20px' }}>Напишите первое сообщение</div>
        ) : (
          messages.map(msg => (
            <div 
              key={msg.id}
              style={{
                alignSelf: msg.is_from_admin ? 'flex-end' : 'flex-start',
                background: msg.is_from_admin ? 'var(--accent)' : 'var(--bg-color)', /* admin = accent, user = dark */
                color: msg.is_from_admin ? '#000' : 'var(--text)',
                padding: '10px 14px',
                borderRadius: '16px',
                borderBottomRightRadius: msg.is_from_admin ? '4px' : '16px',
                borderBottomLeftRadius: !msg.is_from_admin ? '4px' : '16px',
                maxWidth: '85%',
                fontSize: '15px',
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
              }}
            >
              {msg.text}
              <div style={{ fontSize: '10px', textAlign: 'right', marginTop: '4px', opacity: 0.7 }}>
                {new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ padding: '12px', borderTop: '1px solid var(--border)', display: 'flex', gap: '8px', background: 'var(--surface)' }}>
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          placeholder="Сообщение..."
          rows={1}
          style={{
            flex: 1,
            padding: '12px',
            borderRadius: '20px',
            border: '1px solid var(--border)',
            background: 'var(--bg-color)',
            color: 'var(--text)',
            fontSize: '15px',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit'
          }}
          onKeyDown={(e) => {
            // allows Shift+Enter for new line, Enter to send
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendReply();
            }
          }}
        />
        <Button 
          variant="primary" 
          onClick={handleSendReply}
          isLoading={sending}
          style={{ width: '48px', height: '48px', borderRadius: '50%', padding: '0', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center' }}
        >
          {sending ? "" : "✈️"}
        </Button>
      </div>

    </div>
  );
}
