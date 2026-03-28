import React, { useEffect, useState, useCallback } from 'react';
import {
  fetchMe,
  fetchProtocols,
  fetchLink,
  fetchEndpoints,
  selectEndpoint,
  switchProtocol,
  updateSni,
  requestVpn,
} from './api';
import { getTelegram } from './telegram';

import ConnectionCard from './components/ConnectionCard';
import ServerSelector from './components/ServerSelector';
import StatsCard from './components/StatsCard';
import SettingsPanel from './components/SettingsPanel';
import Toast from './components/Toast';
import BottomNav from './components/BottomNav';
import AdminPanel from './components/AdminPanel';
import Card from './ui/Card';
import Button from './ui/Button';

// Mock data for development (when API is not available)
const MOCK_DATA = {
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
  const [activeTab, setActiveTab] = useState('home');
  const [showSettings, setShowSettings] = useState(false);

  // Toast
  const [toast, setToast] = useState({ message: '', type: 'info', visible: false });

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type, visible: true });
    setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: false }));
    }, 3000);
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

  const handleSelectEndpoint = async (name, andCopy = false) => {
    setBusy('endpoint');
    try {
      if (name !== currentEndpoint) {
        await safeFetch(() => selectEndpoint(name), { success: true });
        setCurrentEndpoint(name);
        const linkData = await safeFetch(fetchLink, { link: MOCK_DATA.link });
        setVpnLink(linkData.link);
        showToast('Точка входа изменена.', 'success');
        
        if (andCopy) {
           await navigator.clipboard.writeText(linkData.link);
           setTimeout(() => showToast('Ссылка скопирована!', 'success'), 300);
        }
      } else if (andCopy) {
         handleCopy();
      }
    } catch {
      showToast('Ошибка смены точки входа.', 'error');
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

  const handleRequestVpn = async () => {
    setBusy('request');
    try {
      const resp = await safeFetch(() => requestVpn(), { success: true, message: 'Mock Заявка отправлена' });
      showToast(resp.message || 'Заявка отправлена!', 'success');
      await refreshMe();
    } catch (err) {
      showToast(err.message || 'Ошибка отправки заявки.', 'error');
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
      <header className="header" style={{ marginBottom: activeTab !== 'home' ? '12px' : '0' }}>
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

      <div className="tab-content" style={{ paddingBottom: '70px' }}>
        {activeTab === 'home' && (
          <div className="tab-pane fade-in">
            <ConnectionCard
              profile={me?.profile}
              endpoint={activeEndpoint}
              link={vpnLink}
              onCopy={handleCopy}
              onRequest={handleRequestVpn}
              isBusy={busy === 'request'}
            />
          </div>
        )}

        {activeTab === 'locations' && (
          <div className="tab-pane fade-in">
            {me?.profile?.has_profile ? (
               <ServerSelector
                 endpoints={endpoints}
                 currentEndpoint={currentEndpoint}
                 onSelect={handleSelectEndpoint}
                 onCopy={(name) => handleSelectEndpoint(name, true)}
                 busy={busy === 'endpoint'}
               />
            ) : (
              <Card>
                <div className="empty-state">
                  <div className="empty-icon">📍</div>
                  <div className="empty-title">Нет локаций</div>
                  <div className="empty-text">У тебя пока нет активного профиля VPN для выбора локации.</div>
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'profile' && (
          <div className="tab-pane fade-in">
            <StatsCard
              visible={true}
              onError={(msg) => showToast(msg, 'error')}
            />
            <SettingsPanel
              visible={true}
              profile={me?.profile}
              protocols={protocols}
              onSwitchProtocol={handleSwitchProtocol}
              onUpdateSni={handleUpdateSni}
              busy={busy === 'protocol' || busy === 'sni'}
            />
            <Card style={{ marginTop: '16px' }}>
              <div className="card-title">💬 Поддержка</div>
              <Button
                variant="secondary"
                style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', fontSize: '15px' }}
                onClick={() => {
                  const tg = getTelegram();
                  if (tg?.openTelegramLink) {
                    tg.openTelegramLink('https://t.me/whitebites'); // Replace with actual admin username or take from config
                  } else {
                    window.open('https://t.me/whitebites', '_blank');
                  }
                }}
              >
                Написать администратору
              </Button>
            </Card>
          </div>
        )}

        {activeTab === 'admin' && me?.user?.is_admin && (
          <div className="tab-pane fade-in">
            <AdminPanel onError={(msg) => showToast(msg, 'error')} onSuccess={(msg) => showToast(msg, 'success')} />
          </div>
        )}
      </div>

      <BottomNav activeTab={activeTab} onTabChange={setActiveTab} isAdmin={Boolean(me?.user?.is_admin)} />

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
