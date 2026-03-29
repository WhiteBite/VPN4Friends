import { getInitData } from './telegram';

// use relative /api for production same-origin hosting, dev fallback to localhost
// Use VITE_API_BASE_URL if provided (even in prod for cross-subdomain calls), 
// otherwise fallback to relative /api or localhost.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.PROD ? '/api' : 'http://localhost:8000/api');

async function apiRequest(path, options = {}) {
  const initData = getInitData();

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  // 1. Try to get token from URL first (Magic Link)
  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get('token');
  if (urlToken) {
    localStorage.setItem('auth_token', urlToken);
    // Clean up URL without reload
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // 2. Auth: Prioritize JWT Token from localStorage if available
  const storedToken = localStorage.getItem('auth_token');
  if (storedToken) {
    headers['Authorization'] = `Bearer ${storedToken}`;
  } else if (initData) {
    // 3. Fallback to Telegram Init Data
    headers['X-Telegram-Init-Data'] = initData;
  } else if (!import.meta.env.DEV) {
    // No auth method available
    throw new Error('Требуется авторизация. Откройте приложение через Telegram или используйте команду /web в боте.');
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
  const storedToken = localStorage.getItem('auth_token');

  // Need at least one auth method for WS
  if (!initData && !storedToken && !import.meta.env.DEV) return () => {};

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Derive WS host from API base URL or fall back to current page host
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
  let retryDelay = 2000;       // Start with 2s
  const MAX_DELAY = 30000;     // Cap at 30s
  const MAX_RETRIES = 5;       // Stop reconnecting after 5 failures
  let retryCount = 0;
  let retryTimer = null;
  let closed = false;          // True when user calls unsubscribe

  function connect() {
    if (closed) return;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      retryDelay = 2000; // Reset on successful connect
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
      if (retryCount > MAX_RETRIES) {
        // Stop trying — WS is optional, app works without it
        return;
      }
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

// ----- Admin Users -----

export function fetchUsers() {
  return apiRequest('/staff/users');
}

export function revokeUserVpn(userId) {
  return apiRequest(`/staff/users/${userId}/vpn`, { method: 'DELETE' });
}
