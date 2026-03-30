import React, { useState } from 'react';

/**
 * LoginScreen — shown when the app is opened outside Telegram
 * and no auth token is stored in localStorage.
 * 
 * Two modes:
 * 1. username: enter @username → get instant JWT (if user has VPN)
 * 2. token: paste token from /web bot command
 */
export default function LoginScreen({ onLogin }) {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('username'); // 'username' | 'token'

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

  // Handle username submit — instant JWT if user exists + has VPN
  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const clean = username.trim();
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
        throw new Error(data.detail || 'Не удалось войти');
      }

      if (data.status === 'approved' && data.token) {
        // Instant login
        localStorage.setItem('auth_token', data.token);
        await onLogin();
      } else {
        throw new Error('Неожиданный ответ сервера');
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
        <p className="login-subtitle">Войти в личный кабинет</p>

        {mode === 'username' ? (
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
        ) : (
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

        <div className="login-help">
          <p style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '8px' }}>Телеграм не грузится?</p>
          <a
            href={import.meta.env.VITE_MTPROTO_URL || "tg://proxy?server=vpn4friends-api.whitebite.ru&port=443&secret=dddbab1715494d4d67ab0f5cc76efc250d"}
            className="login-button"
            style={{
              display: 'block',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'var(--text-hint)',
              textAlign: 'center',
              textDecoration: 'none',
              marginBottom: '16px',
            }}
          >
            Подключить публичный Прокси
          </a>
          
          <p>Нет Telegram на этом устройстве?</p>
          <ol>
            <li>Откройте <a href="https://t.me/whitebite_vpn_bot" target="_blank" rel="noopener noreferrer">@whitebite_vpn_bot</a> с телефона</li>
            <li>Отправьте команду <code>/web</code></li>
            <li>Скопируйте токен и {' '}
              <span 
                style={{ color: 'var(--primary)', cursor: 'pointer', textDecoration: 'underline' }}
                onClick={() => { setMode('token'); setError(''); }}
              >
                вставьте сюда
              </span>
            </li>
          </ol>
          {mode === 'token' && (
            <p style={{ textAlign: 'center', marginTop: '16px' }}>
              <span 
                style={{ color: 'var(--text-hint)', cursor: 'pointer', textDecoration: 'underline' }}
                onClick={() => { setMode('username'); setError(''); }}
              >
                Вернуться к вводу @username
              </span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
