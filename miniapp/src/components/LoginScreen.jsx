import React, { useState } from 'react';

/**
 * LoginScreen — shown when the app is opened outside Telegram
 * and no auth token is stored in localStorage.
 * 
 * Users can paste a token from the /web bot command.
 */
export default function LoginScreen({ onLogin }) {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError('Вставьте токен');
      return;
    }

    setLoading(true);
    setError('');

    // Save token and try to load user data
    localStorage.setItem('auth_token', trimmed);

    try {
      // Test the token by calling onLogin
      await onLogin();
    } catch (err) {
      localStorage.removeItem('auth_token');
      setError(err?.message || 'Неверный или просроченный токен');
      setLoading(false);
    }
  };

  return (
    <div className="app" data-theme="dark">
      <div className="login-screen">
        <div className="login-icon">🛡️</div>
        <h1 className="login-title">VPN4Friends</h1>
        <p className="login-subtitle">Войти в личный кабинет</p>

        <form className="login-form" onSubmit={handleSubmit}>
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

        <div className="login-help">
          <p>Как получить токен?</p>
          <ol>
            <li>Откройте <a href="https://t.me/whitebite_vpn_bot" target="_blank" rel="noopener noreferrer">@whitebite_vpn_bot</a></li>
            <li>Отправьте команду <code>/web</code></li>
            <li>Скопируйте токен из ответа бота</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
