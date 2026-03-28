// Mock data for development (when API is not available)
export const MOCK_DATA = {
  me: {
    user: { full_name: 'Даня', username: 'danya', is_admin: true },
    profile: {
      has_profile: false,
      request_status: null,
      protocol: 'vless',
      label: 'VLESS Reality',
      sni: 'google.com',
      available_snis: ['google.com', 'yahoo.com', 'microsoft.com'],
    },
    presets: [],
  },
  protocols: [
    { name: 'vless', label: 'VLESS Reality', description: 'Рекомендуется', recommended: true },
    { name: 'shadowsocks', label: 'Shadowsocks', description: 'Альтернативный', recommended: false },
  ],
  endpoints: [
    { name: 'relay-msk', label: '🇷🇺 Через Москву → NL', host: '***REMOVED***', port: 443, is_relay: true, target: 'direct-nl', description: 'Обход белых списков' },
    { name: 'direct-nl', label: '🇳🇱 Напрямую NL', host: '***REMOVED***', port: 443, is_relay: false, description: 'Hiddify NL' },
    { name: '62yun', label: '🌍 62YUN', host: '***REMOVED***', port: 443, is_relay: false, description: 'Прямое подключение' },
  ],
  link: 'vless://abc123-def456@***REMOVED***:443?type=tcp&security=reality&pbk=MOCK_KEY&fp=chrome&sni=google.com&sid=abcdef&spx=%2F&flow=xtls-rprx-vision#VPN4Friends',
};
