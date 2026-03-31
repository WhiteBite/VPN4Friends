import React, { useEffect, useState, useCallback } from 'react';
import { getTelegram, getInitData, loadTelegramSdk } from './telegram';
import { useVPN } from './hooks/useVPN';
import { useWebSocket } from './hooks/useWebSocket';

import ConnectionCard from './components/ConnectionCard';
import ServerSelector from './components/ServerSelector';
import { copyToClipboard } from './utils/clipboard';
import StatsCard from './components/StatsCard';
import SettingsPanel from './components/SettingsPanel';
import Toast from './components/Toast';
import BottomNav from './components/BottomNav';
import AdminPanel from './components/AdminPanel';
import SupportForm from './components/SupportForm';
import LoginScreen from './components/LoginScreen';
import Card from './ui/Card';
import Button from './ui/Button';



function App() {
  // ----- State -----
  const [colorScheme, setColorScheme] = useState('dark');
  const [activeTab, setActiveTab] = useState('home');
  const [showSettings, setShowSettings] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);

  const [showSupport, setShowSupport] = useState(false);

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
    handleRequestVpn,
    handleRevokeVpn
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
    async function init() {
      // Load Telegram SDK only if we're inside Telegram WebView.
      // Outside Telegram (browser), this resolves immediately with false
      // so users in Russia aren't blocked by RKN filtering telegram.org.
      await loadTelegramSdk();

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
        try {
          await loadAll();
        } catch {
          localStorage.removeItem('auth_token');
          setNeedsAuth(true);
        }
        return;
      }

      // Always attempt to load data first.
      // Even if getInitData() returns empty now, the apiRequest function
      // will re-check initData at call time (URL hash may contain it).
      const initData = getInitData();
      const storedToken = localStorage.getItem('auth_token');

      // If we clearly have no auth method, show login immediately
      if (!initData && !storedToken && !import.meta.env.DEV) {
        // But double-check: are we inside Telegram? (hash might have data)
        const hash = window.location.hash || '';
        if (hash.includes('tgWebAppData')) {
          // We ARE inside Telegram, try loading anyway
          try {
            await loadAll();
          } catch {
            setNeedsAuth(true);
          }
        } else {
          setNeedsAuth(true);
        }
      } else {
        try {
          await loadAll();
        } catch {
          // If loadAll fails and we have no auth fallback, show login
          if (!getInitData() && !localStorage.getItem('auth_token')) {
            setNeedsAuth(true);
          }
        }
      }
    }

    init();
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

  const getFullSubscriptionUrl = () => {
    const subUrl = me?.subscription_url;
    if (!subUrl) return '';
    const origin = import.meta.env.VITE_API_BASE_URL 
      ? new URL(import.meta.env.VITE_API_BASE_URL, window.location.href).origin
      : 'https://vpn4friends-api.whitebite.ru';
    return `${origin}${subUrl}`;
  };

  const handleCopySubscription = () => {
    const fullUrl = getFullSubscriptionUrl();
    if (!fullUrl) {
      showToast('Подписка недоступна.', 'error');
      return;
    }
    
    copyToClipboard(
      fullUrl,
      () => showToast('Ссылка на подписку скопирована!', 'success'),
      () => showToast('Не удалось скопировать. Выделите текст и скопируйте.', 'error')
    );
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
              subscriptionUrl={getFullSubscriptionUrl()}
              onCopySubscription={handleCopySubscription}
              onRequest={handleRequestVpn}
              isBusy={busy === 'request'}
            />
          </div>
        )}

        {activeTab === 'locations' && (
          <div className="tab-pane fade-in">
            {me?.profile?.has_profile ? (
              <>
                <div style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: '12px',
                  padding: '12px 16px',
                  marginBottom: '16px',
                  fontSize: '13px',
                  color: 'var(--text-hint)',
                  lineHeight: '1.4'
                }}>
                  ℹ️ Если вы используете <b>подписку</b> (со вкладки «Главная») — все серверы уже добавлены автоматически.
                  Здесь можно скопировать ссылку на <b>конкретный сервер</b> для ручной настройки.
                </div>
                <ServerSelector
                  endpoints={endpoints}
                  currentEndpoint={currentEndpoint}
                  onSelect={handleSelectEndpoint}
                  onCopy={(name) => handleSelectEndpoint(name, true)}
                  busy={busy === 'endpoint'}
                />
              </>
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
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <div style={{ background: 'var(--primary)', color: '#fff', width: '40px', height: '40px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '16px' }}>
                  {me?.user?.full_name ? me.user.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '15px' }}>{me?.user?.full_name || 'Пользователь'}</div>
                  <div style={{ color: 'var(--text-hint)', fontSize: '13px' }}>@{me?.user?.username || 'Без имени'}</div>
                </div>
              </div>

              {me?.profile?.has_profile && (
                <div className="stat-row">
                  <div className="stat-label">VPN-клиент ID</div>
                  <div className="stat-value" style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {me.profile.client_id ? `${me.profile.client_id.substring(0, 8)}...` : 'Неизвестно'}
                  </div>
                </div>
              )}
            </Card>
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
              onRevokeVpn={handleRevokeVpn}
              busy={busy === 'protocol' || busy === 'sni' || busy === 'revoke'}
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

      {/* Floating Support Button */}
      {me?.user && (
        <>
          <button
            className="fab-support"
            onClick={() => setShowSupport(!showSupport)}
            title="Поддержка"
          >
            {showSupport ? '✕' : '💬'}
          </button>
          {showSupport && (
            <div className="support-modal-overlay" onClick={() => setShowSupport(false)}>
              <div className="support-modal" onClick={e => e.stopPropagation()}>
                <SupportForm
                  onError={(msg) => showToast(msg, 'error')}
                  onSuccess={(msg) => { showToast(msg, 'success'); setShowSupport(false); }}
                />
              </div>
            </div>
          )}
        </>
      )}

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
