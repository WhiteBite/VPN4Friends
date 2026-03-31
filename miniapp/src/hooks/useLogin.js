import { useState, useEffect, useRef } from 'react';

export function useLogin(onLogin) {
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

  // Poll status when in 'pending' mode
  useEffect(() => {
    if (mode !== 'pending' || !pollToken) return;

    const poll = async () => {
      try {
        const res = await fetch(`/api/auth/poll-status?poll_token=${pollToken}`);
        const data = await res.json();

        if (data.status === 'approved' && data.token) {
          if (pollInterval.current) clearInterval(pollInterval.current);
          localStorage.setItem('auth_token', data.token);
          await onLogin();
        } else if (data.status === 'rejected') {
          if (pollInterval.current) clearInterval(pollInterval.current);
          setMode('username');
          setError('Заявка отклонена администратором. Попробуйте ещё раз.');
          setPollToken(null);
        }
      } catch (err) {
        console.warn('Poll error:', err);
      }
    };

    poll();
    pollInterval.current = setInterval(poll, 3000);

    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [mode, pollToken, onLogin]);

  const handleTokenSubmit = async (e) => {
    if (e) e.preventDefault();
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

  const handleUsernameSubmit = async (e) => {
    if (e) e.preventDefault();
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
        localStorage.setItem('auth_token', data.token);
        await onLogin();
      } else if (data.status === 'pending' && data.poll_token) {
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

  const cancelPending = () => {
    if (pollInterval.current) clearInterval(pollInterval.current);
    setMode('username');
    setPollToken(null);
    setError('');
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setError('');
  };

  return {
    mode,
    switchMode,
    username,
    setUsername,
    token,
    setToken,
    error,
    loading,
    pendingMessage,
    handleUsernameSubmit,
    handleTokenSubmit,
    cancelPending,
  };
}
