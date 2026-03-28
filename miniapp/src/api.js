import { getInitData } from './telegram';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function apiRequest(path, options = {}) {
  const initData = getInitData();

  // If initData is empty and we are not in mock dev mode, we cannot authenticate the user.
  if (!initData && !import.meta.env.DEV) {
    throw new Error('Telegram не передал данные профиля (initData пуст). Перезапустите бота через /start и нажмите кнопку в меню.');
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  let data;
  let rawText;
  try {
    rawText = await response.text();
    if (rawText) data = JSON.parse(rawText);
  } catch {
    // Ignore non-json body
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    if (data) {
      message = data.detail || data.message || message;
    } else if (rawText) {
      message = rawText;
    }
    throw new Error(message);
  }

  if (data && data.success === false) {
    throw new Error(data.message || 'Ошибка выполнения');
  }

  return Object.keys(data || {}).length > 0 ? data : null;
}

// ----- User state -----

export function subscribeToWebSockets(callbacks = {}) {
  const initData = getInitData();
  if (!initData && !import.meta.env.DEV) return () => {};

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = import.meta.env.VITE_API_BASE_URL 
    ? import.meta.env.VITE_API_BASE_URL.replace(/^http(s)?:\/\//, '')
    : 'localhost:8000';
  const wsUrl = `${protocol}//${host}/ws?init_data=${encodeURIComponent(initData || '')}`;

  let ws = null;
  let retryDelay = 1000;       // Start with 1s
  const MAX_DELAY = 30000;     // Cap at 30s
  let retryTimer = null;
  let closed = false;          // True when user calls unsubscribe

  function connect() {
    if (closed) return;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      retryDelay = 1000; // Reset on successful connect
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
      // Auto-reconnect with exponential backoff
      retryTimer = setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, MAX_DELAY);
        connect();
      }, retryDelay);
    };

    ws.onerror = () => {
      // onclose will fire after onerror, so reconnect is handled there
    };
  }

  connect();

  // Return cleanup function
  return () => {
    closed = true;
    if (retryTimer) clearTimeout(retryTimer);
    if (ws) {
      ws.onclose = null; // Prevent reconnect on intentional close
      ws.close();
      ws = null;
    }
  };
}

export function fetchMe() {
  return apiRequest('/me');
}

export function fetchProtocols() {
  return apiRequest('/protocols');
}

// ----- VPN Link (direct, no preset needed) -----

export function fetchLink() {
  return apiRequest('/me/link');
}

// ----- Stats -----

export function fetchStats() {
  return apiRequest('/me/stats');
}

// ----- Endpoints -----

export function fetchEndpoints() {
  return apiRequest('/endpoints');
}

export function selectEndpoint(endpoint) {
  return apiRequest('/me/endpoint', {
    method: 'POST',
    body: JSON.stringify({ endpoint }),
  });
}

// ----- Protocol / SNI -----

export function switchProtocol(protocol) {
  return apiRequest('/me/protocol', {
    method: 'POST',
    body: JSON.stringify({ protocol }),
  });
}

export function updateSni(sni) {
  return apiRequest('/me/sni', {
    method: 'POST',
    body: JSON.stringify({ sni }),
  });
}

// ----- VPN Requests & Admin -----

export function requestVpn(comment = '') {
  return apiRequest('/me/request', { 
    method: 'POST',
    body: JSON.stringify({ comment }),
  });
}

export function fetchAdminRequests() {
  return apiRequest('/staff/requests');
}

export function approveRequest(id) {
  return apiRequest(`/staff/requests/${id}/approve`, { method: 'POST' });
}

export function rejectRequest(id) {
  return apiRequest(`/staff/requests/${id}/reject`, { method: 'POST' });
}

export function sendAdminBroadcast(payload) {
  return apiRequest('/staff/broadcast', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ----- Support Chats -----

export function fetchAdminChats() {
  return apiRequest('/staff/chats');
}

export function fetchChatHistory(userId) {
  return apiRequest(`/staff/chats/${userId}`);
}

export function sendChatReply(userId, text) {
  return apiRequest(`/staff/chats/${userId}`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

// ----- Presets -----

export function listPresets() {
  return apiRequest('/presets');
}

export function createPreset(payload) {
  return apiRequest('/presets', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function deletePreset(id) {
  return apiRequest(`/presets/${id}`, { method: 'DELETE' });
}

export function getPresetConfig(id) {
  return apiRequest(`/presets/${id}/config`);
}

// ----- Support/Help -----

export function sendSupportMessage(text) {
  return apiRequest('/support', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}
