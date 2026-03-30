import React, { useEffect, useState, useCallback } from 'react';
import { getTelegram } from './telegram';
import { useVPN } from './hooks/useVPN';
import { useWebSocket } from './hooks/useWebSocket';

import ConnectionCard from './components/ConnectionCard';
import ServerSelector from './components/ServerSelector';
import StatsCard from './components/StatsCard';
import SettingsPanel from './components/SettingsPanel';
import Toast from './components/Toast';
import BottomNav from './components/BottomNav';
import AdminPanel from './components/AdminPanel';
import SupportForm from './components/SupportForm';
import LoginScreen from './components/LoginScreen';
import Card from './ui/Card';
import Button from './ui/Button';
import { getInitData } from './telegram';



function App() {
  // ----- State -----
  const [colorScheme, setColorScheme] = useState('dark');
  const [activeTab, setActiveTab] = useState('home');
  const [showSettings, setShowSettings] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);

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

  const {
    loading,
    me,
    protocols,
    endpoints,
    currentEndpoint,
    vpnLink,
    busy,
    loadAll,
    refreshMe,
    handleSelectEndpoint,
    handleSwitchProtocol,
    handleUpdateSni,
    handleRequestVpn
  } = useVPN(showToast);

  // Setup WebSockets
  useWebSocket({
    NEW_REQUEST: (msg) => {
      showToast(`Новая заявка VPN от ${msg.full_name}`, 'success');
      // Dispatch custom DOM event to trigger AdminPanel refresh
      window.dispatchEvent(new Event('refresh_admin_data'));
    },
    REQUEST_APPROVED: () => {
      showToast('Ваш VPN одобрен!', 'success');
      loadAll(); // Reload everything to get the link
    },
    REQUEST_REJECTED: () => {
      showToast('Заявка на VPN отклонена', 'error');
      refreshMe();
    }
  });

  // ----- Init (runs once on mount) -----
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

    // Check for ?token= in URL (from /web bot command)
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    if (urlToken) {
      // Save token and clean URL
      localStorage.setItem('auth_token', urlToken);
      window.history.replaceState({}, '', window.location.pathname);
      // Auto-login with this token
      loadAll().catch(() => {
        localStorage.removeItem('auth_token');
        setNeedsAuth(true);
      });
      return;
    }

    // Check if we have any auth method available
    const initData = getInitData();
    const storedToken = localStorage.getItem('auth_token');

    if (!initData && !storedToken && !import.meta.env.DEV) {
      // No auth available — show login screen
      setNeedsAuth(true);
      // No auth, no loading needed
    } else {
      loadAll().catch(() => {
        // If loadAll fails due to auth, show login
        if (!initData && !localStorage.getItem('auth_token')) {
          setNeedsAuth(true);
        }
      });
    }
  }, []);

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

  const handleCopySubscription = async () => {
    const subUrl = me?.subscription_url;
    if (!subUrl) {
      showToast('Подписка недоступна.', 'error');
      return;
    }
    const fullUrl = `${window.location.origin}${subUrl}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
      showToast('Ссылка на подписку скопирована!', 'success');
    } catch {
      showToast('Не удалось скопировать.', 'error');
    }
  };

  // ----- Render -----

  const activeEndpoint = endpoints.find((ep) => ep.name === currentEndpoint) || null;

  // ----- Auth gate -----
  if (needsAuth) {
    return (
      <LoginScreen
        onLogin={async () => {
          await loadAll();
          setNeedsAuth(false);
        }}
      />
    );
  }

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
            {me?.subscription_url && (
              <Card>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ fontSize: '28px' }}>📡</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '15px', marginBottom: '4px' }}>Авто-подписка</div>
                    <div style={{ fontSize: '12px', opacity: 0.6 }}>Добавь в Throne / v2rayNG — сервера обновятся автоматически</div>
                  </div>
                  <Button size="sm" onClick={handleCopySubscription}>Копировать</Button>
                </div>
              </Card>
            )}
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
            <SupportForm 
              onError={(msg) => showToast(msg, 'error')} 
              onSuccess={(msg) => showToast(msg, 'success')} 
            />
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
