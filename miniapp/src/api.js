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
      const text = await response.text();
      if (text) {
        message = text;
      }
    } catch (e) {
      // ignore
    }
    throw new Error(message);
  }

  return response.json();
}

export function fetchMe() {
  return apiRequest('/me');
}

export function fetchProtocols() {
  return apiRequest('/protocols');
}

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
  return apiRequest(`/presets/${id}`, {
    method: 'DELETE',
  });
}

export function getPresetConfig(id) {
  return apiRequest(`/presets/${id}/config`);
}
