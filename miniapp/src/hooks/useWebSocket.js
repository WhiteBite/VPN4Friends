import { useEffect } from 'react';
import { getInitData } from '../telegram';
import { API_BASE_URL } from '../api';

function subscribeToWebSockets(callbacks = {}) {
  const initData = getInitData();
  const storedToken = localStorage.getItem('auth_token');

  if (!initData && !storedToken && !import.meta.env.DEV) return () => {};

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  let wsHost = window.location.host;
  try {
    const apiUrl = new URL(API_BASE_URL);
    wsHost = apiUrl.host;
  } catch { /* use page host */ }

  let wsUrl = `${protocol}//${wsHost}/ws`;
  if (storedToken) {
    wsUrl += `?token=${encodeURIComponent(storedToken)}`;
  } else if (initData) {
    wsUrl += `?init_data=${encodeURIComponent(initData)}`;
  }

  let ws = null;
  let retryDelay = 2000;
  const MAX_DELAY = 30000;
  const MAX_RETRIES = 5;
  let retryCount = 0;
  let retryTimer = null;
  let closed = false;

  function connect() {
    if (closed) return;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      retryDelay = 2000;
      retryCount = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (callbacks[data.type]) {
          callbacks[data.type](data);
        }
      } catch { /* ignore malformed messages */ }
    };

    ws.onclose = () => {
      if (closed) return;
      retryCount++;
      if (retryCount > MAX_RETRIES) return;
      retryTimer = setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, MAX_DELAY);
        connect();
      }, retryDelay);
    };

    ws.onerror = () => {};
  }

  connect();

  return () => {
    closed = true;
    if (retryTimer) clearTimeout(retryTimer);
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
  };
}

export function useWebSocket(handlers) {
  useEffect(() => {
    const unsubscribe = subscribeToWebSockets(handlers);
    return () => {
      unsubscribe();
    };
  }, [handlers]);
}
