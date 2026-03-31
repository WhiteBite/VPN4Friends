import React, { useState, useEffect, useRef } from 'react';

/**
 * LoginScreen — shown when the app is opened outside Telegram.
 * 
 * Three modes:
 * 1. username: enter @username → server decides: instant login or pending approval
 * 2. pending: auto-poll every 3s waiting for admin approval
 * 3. token: paste JWT token from /web bot command
 */

// Public proxy links (hardcoded — these are public endpoints)
const PROXY_LINKS = [
  {
    label: '🇫🇮 Финляндия MTProto',
    url: 'tg://proxy?server=fi.vpn4friends.whitebite.ru&port=4443&secret=***REMOVED***',
    type: 'mtproto',
  },
  {
    label: '🇩🇪 Германия MTProto',
    url: 'tg://proxy?server=de.vpn4friends.whitebite.ru&port=4443&secret=***REMOVED***',
    type: 'mtproto',
  },
];

export default function LoginScreen({ onLogin }) {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('username'); // 'username' | 'pending' | 'token'
  const [pollToken, setPollToken] = useState(null);
  const [pendingMessage, setPendingMessage] = useState('');
  const pollInterval = useRef(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  // Start polling when we have a poll token
  useEffect(() => {
    if (mode !== 'pending' || !pollToken) return;

    const poll = async () => {
      try {
        const res = await fetch(`/api/auth/poll-status?poll_token=${pollToken}`);
        const data = await res.json();

        if (data.status === 'approved' && data.token) {
          // Success! Admin approved
          if (pollInterval.current) clearInterval(pollInterval.current);
          localStorage.setItem('auth_token', data.token);
          await onLogin();
        } else if (data.status === 'rejected') {
          if (pollInterval.current) clearInterval(pollInterval.current);
          setMode('username');
          setError('Заявка отклонена администратором. Попробуйте ещё раз.');
          setPollToken(null);
        }
        // else: still pending, keep polling
      } catch (err) {
        // Network error, keep trying
        console.warn('Poll error:', err);
      }
    };

    // Poll immediately and then every 3 seconds
    poll();
    pollInterval.current = setInterval(poll, 3000);

    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [mode, pollToken, onLogin]);

  // Handle direct JWT token login (from /web command)
  const handleTokenSubmit = async (e) => {
    e.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError('Вставьте токен');
      return;
    }

    setLoading(true);
    setError('');

    localStorage.setItem('auth_token', trimmed);

    try {
      await onLogin();
    } catch (err) {
      localStorage.removeItem('auth_token');
      setError(err?.message || 'Неверный или просроченный токен');
      setLoading(false);
    }
  };

  // Handle username submit — instant JWT if approved, or pending state
  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const clean = username.trim().replace(/^@/, '');
    if (!clean || clean.length < 2) {
      setError('Введите корректный @username');
      return;
    }

    setLoading(true);

    try {
      const res = await fetch('/api/auth/request-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: clean })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Ошибка сервера');
      }

      if (data.status === 'approved' && data.token) {
        // Instant login — user already has VPN
        localStorage.setItem('auth_token', data.token);
        await onLogin();
      } else if (data.status === 'pending' && data.poll_token) {
        // Need admin approval — switch to polling mode
        setPollToken(data.poll_token);
        setPendingMessage(data.message || 'Заявка отправлена! Ожидайте одобрения.');
        setMode('pending');
        setLoading(false);
      } else {
        throw new Error(data.message || 'Неожиданный ответ сервера');
      }
    } catch (err) {
      setLoading(false);
      setError(err.message);
    }
  };

  return (
    <div className="app" data-theme="dark">
      <div className="login-screen">
        <div className="login-icon">🛡️</div>
        <h1 className="login-title">VPN4Friends</h1>
        <p className="login-subtitle">
          {mode === 'pending' ? 'Ожидание одобрения' : 'Войти в личный кабинет'}
        </p>

        {/* ---- MODE: PENDING ---- */}
        {mode === 'pending' && (
          <div style={{ 
            textAlign: 'center', 
            padding: '24px 16px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
          }}>
            {/* Animated spinner */}
            <div style={{
              width: '64px',
              height: '64px',
              border: '3px solid rgba(255,255,255,0.1)',
              borderTop: '3px solid var(--primary, #3b82f6)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }} />
            
            <div style={{
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '16px',
              padding: '20px',
              maxWidth: '320px',
            }}>
              <div style={{ fontSize: '18px', fontWeight: '700', marginBottom: '8px' }}>
                📋 Заявка отправлена
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-hint)', lineHeight: '1.5' }}>
                {pendingMessage}
              </div>
              <div style={{ 
                fontSize: '12px', 
                color: 'var(--text-muted)', 
                marginTop: '12px',
                opacity: 0.7,
              }}>
                Страница обновится автоматически после одобрения
              </div>
            </div>

            <button
              className="login-button"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: 'var(--text-hint)',
                marginTop: '8px',
                maxWidth: '320px',
              }}
              onClick={() => {
                if (pollInterval.current) clearInterval(pollInterval.current);
                setMode('username');
                setPollToken(null);
                setError('');
              }}
            >
              ← Вернуться
            </button>
          </div>
        )}

        {/* ---- MODE: USERNAME ---- */}
        {mode === 'username' && (
          <form className="login-form" onSubmit={handleUsernameSubmit}>
            <div className="login-input-group">
              <input
                type="text"
                className="login-input"
                placeholder="Ваш @username в Telegram"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                disabled={loading}
              />
            </div>
            {error && <div className="login-error">{error}</div>}
            <button
              type="submit"
              className="login-button"
              disabled={loading || !username.trim()}
            >
              {loading ? 'Загрузка...' : 'Войти'}
            </button>
          </form>
        )}

        {/* ---- MODE: TOKEN ---- */}
        {mode === 'token' && (
          <form className="login-form" onSubmit={handleTokenSubmit}>
            <div className="login-input-group">
              <input
                type="text"
                className="login-input"
                placeholder="Вставьте токен из бота"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoFocus
                disabled={loading}
              />
            </div>
            {error && <div className="login-error">{error}</div>}
            <button
              type="submit"
              className="login-button"
              disabled={loading || !token.trim()}
            >
              {loading ? 'Проверяю...' : 'Войти'}
            </button>
          </form>
        )}

        {/* ---- HELP SECTION ---- */}
        {mode !== 'pending' && (
          <div className="login-help">
            {/* Proxy links section */}
            <div style={{
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.15)',
              borderRadius: '16px',
              padding: '16px',
              marginBottom: '20px',
            }}>
              <p style={{ 
                fontWeight: 700, 
                color: 'var(--text)', 
                marginBottom: '12px',
                fontSize: '15px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                ✈️ Telegram заблокирован?
              </p>
              <p style={{ 
                fontSize: '13px', 
                color: 'var(--text-hint)', 
                marginBottom: '12px',
                lineHeight: '1.4',
              }}>
                Подключите бесплатный прокси, чтобы Telegram снова заработал:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {PROXY_LINKS.map((proxy, idx) => (
                  <a
                    key={idx}
                    href={proxy.url}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '12px 14px',
                      borderRadius: '12px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      textDecoration: 'none',
                      color: 'var(--text)',
                      fontSize: '14px',
                      fontWeight: '500',
                      transition: 'all 0.2s',
                    }}
                  >
                    <span style={{ fontSize: '18px' }}>{proxy.label.slice(0, 4)}</span>
                    <span style={{ flex: 1 }}>{proxy.label.slice(4).trim()}</span>
                    <span style={{ 
                      fontSize: '11px', 
                      color: 'var(--text-muted)',
                      background: 'rgba(255,255,255,0.05)',
                      padding: '3px 8px',
                      borderRadius: '6px',
                    }}>
                      Подключить
                    </span>
                  </a>
                ))}
              </div>
            </div>

            {/* Token fallback */}
            <p style={{ fontSize: '13px', color: 'var(--text-hint)' }}>
              Есть токен от бота?{' '}
              <span 
                style={{ color: 'var(--primary)', cursor: 'pointer', textDecoration: 'underline' }}
                onClick={() => { setMode('token'); setError(''); }}
              >
                Войти по токену
              </span>
            </p>
            {mode === 'token' && (
              <p style={{ textAlign: 'center', marginTop: '12px' }}>
                <span 
                  style={{ color: 'var(--text-hint)', cursor: 'pointer', textDecoration: 'underline', fontSize: '13px' }}
                  onClick={() => { setMode('username'); setError(''); }}
                >
                  Вернуться к вводу @username
                </span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* Inline CSS for spinner animation */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
