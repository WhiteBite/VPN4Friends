import { getInitData } from './telegram';

// use relative /api for production same-origin hosting, dev fallback to localhost
// Use VITE_API_BASE_URL if provided (even in prod for cross-subdomain calls), 
// otherwise fallback to relative /api or localhost.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
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

export function fetchMe() {
  return apiRequest('/me');
}

export function fetchProtocols() {
  return apiRequest('/auth/protocols');
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
  return apiRequest('/me/endpoints');
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

export function fetchAdminServerStats() {
  return apiRequest('/staff/servers/status');
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

export function revokeMe() {
  return apiRequest('/me/revoke', { method: 'DELETE' });
}
