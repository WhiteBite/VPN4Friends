import React, { useEffect, useState, useCallback } from 'react';
import {
  fetchMe,
  fetchProtocols,
  fetchLink,
  fetchEndpoints,
  selectEndpoint,
  switchProtocol,
  updateSni,
} from './api';
import { getTelegram } from './telegram';

import ConnectionCard from './components/ConnectionCard';
import ServerSelector from './components/ServerSelector';
import QuickActions from './components/QuickActions';
import QRModal from './components/QRModal';
import StatsCard from './components/StatsCard';
import SettingsPanel from './components/SettingsPanel';
import Toast from './components/Toast';

// Mock data for development (when API is not available)
const MOCK_DATA = {
  me: {
    user: { full_name: 'Даня', username: 'danya' },
    profile: {
      has_profile: true,
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

const isDev = import.meta.env.DEV;

async function safeFetch(fetcher, fallback) {
  try {
    return await fetcher();
  } catch {
    if (isDev && fallback !== undefined) return fallback;
    throw new Error('API unavailable');
  }
}

function App() {
  // ----- State -----
  const [colorScheme, setColorScheme] = useState('dark');
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState(null);
  const [protocols, setProtocols] = useState([]);
  const [endpoints, setEndpoints] = useState([]);
  const [currentEndpoint, setCurrentEndpoint] = useState(null);
  const [vpnLink, setVpnLink] = useState(null);
  const [busy, setBusy] = useState('');
  const [showQR, setShowQR] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Toast
  const [toast, setToast] = useState({ message: '', type: 'info', visible: false });

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type, visible: true });
  }, []);

  const hideToast = useCallback(() => {
    setToast((prev) => ({ ...prev, visible: false }));
  }, []);

  // ----- Init -----
  useEffect(() => {
    const tg = getTelegram();
    if (tg) {
      try {
        tg.ready();
        tg.expand();
      } catch {
        // ignore
      }
      if (tg.colorScheme) {
        setColorScheme(tg.colorScheme);
      }
    }
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [meData, protocolData, endpointData] = await Promise.all([
        safeFetch(fetchMe, MOCK_DATA.me),
        safeFetch(fetchProtocols, MOCK_DATA.protocols),
        safeFetch(fetchEndpoints, MOCK_DATA.endpoints),
      ]);

      setMe(meData);
      setProtocols(protocolData);
      setEndpoints(endpointData);
      if (endpointData.length > 0) setCurrentEndpoint(endpointData[0].name);

      // Load VPN link if user has profile
      if (meData?.profile?.has_profile) {
        try {
          const linkData = await safeFetch(fetchLink, { link: MOCK_DATA.link });
          setVpnLink(linkData.link);
        } catch {
          // noop
        }
      }
    } catch {
      showToast('Не удалось загрузить данные.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const refreshMe = async () => {
    try {
      const data = await safeFetch(fetchMe, MOCK_DATA.me);
      setMe(data);
    } catch {
      showToast('Ошибка обновления данных.', 'error');
    }
  };

  const refreshLink = async () => {
    try {
      const linkData = await safeFetch(fetchLink, { link: MOCK_DATA.link });
      setVpnLink(linkData.link);
    } catch {
      // noop
    }
  };

  // ----- Handlers -----

  const handleCopy = async () => {
    if (!vpnLink) {
      showToast('Ссылка ещё не загружена.', 'error');
      return;
    }
    try {
      await navigator.clipboard.writeText(vpnLink);
      showToast('Ссылка скопирована!', 'success');
    } catch {
      showToast('Не удалось скопировать.', 'error');
    }
  };

  const handleSelectEndpoint = async (name) => {
    setBusy('endpoint');
    try {
      await safeFetch(() => selectEndpoint(name), { success: true });
      setCurrentEndpoint(name);
      await refreshLink();
      showToast('Точка входа изменена.', 'success');
    } catch {
      showToast('Не удалось сменить точку входа.', 'error');
    } finally {
      setBusy('');
    }
  };

  const handleSwitchProtocol = async (protocol) => {
    setBusy('protocol');
    try {
      await safeFetch(() => switchProtocol(protocol), { success: true });
      await refreshMe();
      await refreshLink();
      showToast('Протокол переключён.', 'success');
    } catch {
      showToast('Не удалось переключить протокол.', 'error');
    } finally {
      setBusy('');
    }
  };

  const handleUpdateSni = async (sni) => {
    setBusy('sni');
    try {
      await safeFetch(() => updateSni(sni), { success: true });
      await refreshMe();
      await refreshLink();
      showToast('SNI обновлён.', 'success');
    } catch {
      showToast('Не удалось обновить SNI.', 'error');
    } finally {
      setBusy('');
    }
  };

  // ----- Render -----

  const activeEndpoint = endpoints.find((ep) => ep.name === currentEndpoint) || null;

  if (loading) {
    return (
      <div className="app" data-theme={colorScheme}>
        <header className="header">
          <div className="header-icon">🛡</div>
          <div className="header-text">
            <div className="title">VPN4Friends</div>
            <div className="subtitle">Загрузка...</div>
          </div>
        </header>
        <section className="card">
          <div className="skeleton-group">
            <div className="skeleton skeleton--text skeleton--text-long" />
            <div className="skeleton skeleton--text skeleton--text-short" />
            <div className="skeleton skeleton--box" />
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="app" data-theme={colorScheme}>
      {/* Header */}
      <header className="header">
        <div className="header-icon">🛡</div>
        <div className="header-text">
          <div className="title">VPN4Friends</div>
          <div className="subtitle">
            {me?.user?.full_name
              ? `Привет, ${me.user.full_name} 👋`
              : 'Твой VPN-кабинет'}
          </div>
        </div>
      </header>

      {/* Connection Status */}
      <ConnectionCard
        profile={me?.profile}
        endpoint={activeEndpoint}
        link={vpnLink}
        onCopy={handleCopy}
      />

      {/* Quick Actions */}
      <QuickActions
        hasProfile={me?.profile?.has_profile}
        onCopy={handleCopy}
        onQR={() => setShowQR(true)}
        onStats={() => setShowStats((v) => !v)}
      />

      {/* Server Selection */}
      <ServerSelector
        endpoints={endpoints}
        current={currentEndpoint}
        onSelect={handleSelectEndpoint}
        busy={busy === 'endpoint'}
      />

      {/* Stats (lazy) */}
      <StatsCard
        visible={showStats}
        onError={(msg) => showToast(msg, 'error')}
      />

      {/* Settings Toggle */}
      {me?.profile?.has_profile && (
        <button
          type="button"
          className="btn btn--ghost btn--full"
          onClick={() => setShowSettings((v) => !v)}
        >
          {showSettings ? '▲ Скрыть настройки' : '⚙️ Расширенные настройки'}
        </button>
      )}

      {/* Settings Panel */}
      <SettingsPanel
        visible={showSettings}
        profile={me?.profile}
        protocols={protocols}
        onSwitchProtocol={handleSwitchProtocol}
        onUpdateSni={handleUpdateSni}
        busy={!!busy}
      />

      {/* QR Modal */}
      <QRModal
        link={vpnLink}
        visible={showQR}
        onClose={() => setShowQR(false)}
      />

      {/* Toast */}
      <Toast
        message={toast.message}
        type={toast.type}
        visible={toast.visible}
        onHide={hideToast}
      />
    </div>
  );
}

export default App;
