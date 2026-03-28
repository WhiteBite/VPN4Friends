import { getInitData } from './telegram';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function apiRequest(path, options = {}) {
  const initData = getInitData();

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

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      try {
        message = await response.text() || message;
      } catch {
        // ignore
      }
    }
    throw new Error(message);
  }

  return response.json();
}

// ----- User state -----

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

export function requestVpn() {
  return apiRequest('/me/request', { method: 'POST' });
}

export function fetchAdminRequests() {
  return apiRequest('/admin/requests');
}

export function approveRequest(id) {
  return apiRequest(`/admin/requests/${id}/approve`, { method: 'POST' });
}

export function rejectRequest(id) {
  return apiRequest(`/admin/requests/${id}/reject`, { method: 'POST' });
}

export function sendAdminBroadcast(payload) {
  return apiRequest('/admin/broadcast', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ----- Support Chats -----

export function fetchAdminChats() {
  return apiRequest('/admin/chats');
}

export function fetchChatHistory(userId) {
  return apiRequest(`/admin/chats/${userId}`);
}

export function sendChatReply(userId, text) {
  return apiRequest(`/admin/chats/${userId}`, {
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
