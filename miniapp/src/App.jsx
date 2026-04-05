import React, { useEffect, useState, useCallback } from 'react';
import { getTelegram, getInitData, loadTelegramSdk } from './telegram';
import { useVPN } from './hooks/useVPN';
import { useWebSocket } from './hooks/useWebSocket';

import { lazy, Suspense } from 'react';

const ConnectionCard = lazy(() => import('./components/ConnectionCard'));
const ServerSelector = lazy(() => import('./components/ServerSelector'));
const StatsCard = lazy(() => import('./components/StatsCard'));
const SettingsPanel = lazy(() => import('./components/SettingsPanel'));
const BottomNav = lazy(() => import('./components/BottomNav'));
const AdminPanel = lazy(() => import('./components/AdminPanel'));
const SupportForm = lazy(() => import('./components/SupportForm'));
const LoginScreen = lazy(() => import('./components/LoginScreen'));
const Toast = lazy(() => import('./components/Toast'));
import { copyToClipboard } from './utils/clipboard';
import Card from './ui/Card';
import Button from './ui/Button';

const APP_VERSION = "1.0.44";


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
      : 'https://vpn4friends-api.whitebite.ru:8443';
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
      <Suspense fallback={<div style={{padding: '20px', textAlign: 'center'}}>Загрузка интерфейса...</div>}>
      <LoginScreen
        onLogin={async () => {
          await loadAll();
          setNeedsAuth(false);
        }}
      />
      </Suspense>
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

      <div className="tab-content" style={{ paddingBottom: 'calc(120px + env(safe-area-inset-bottom))' }}>
        <Suspense fallback={<div style={{padding: '20px', textAlign: 'center'}}>Загрузка интерфейса...</div>}>
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
                  background: 'rgba(14, 165, 233, 0.06)',
                  border: '1px solid rgba(14, 165, 233, 0.12)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  marginBottom: '16px',
                  fontSize: '12px',
                  color: '#94A3B8',
                  lineHeight: '1.4',
                  display: 'flex',
                  gap: '8px',
                  alignItems: 'center',
                }}>
                  <span style={{ fontSize: '14px', flexShrink: 0 }}>💡</span>
                  <span>Здесь находится каталог серверов. Если вы настроили подписку во вкладке «Главная» — все они уже добавлены в ваше приложение. Этот список нужен только для добавления серверов вручную по одному.</span>
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
            <Card style={{ padding: '24px', overflow: 'hidden', position: 'relative' }}>
              {/* Decorative glow */}
              <div style={{ position: 'absolute', top: '-30px', right: '-30px', width: '100px', height: '100px', background: 'var(--primary)', filter: 'blur(60px)', opacity: 0.1, borderRadius: '50%' }} />
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px', position: 'relative' }}>
                <div style={{ 
                  background: 'linear-gradient(135deg, #0EA5E9, #3B82F6)', 
                  color: '#fff', 
                  width: '48px', height: '48px', 
                  borderRadius: '14px', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center', 
                  fontWeight: 'bold', fontSize: '20px',
                  boxShadow: '0 4px 12px rgba(14, 165, 233, 0.3)',
                  flexShrink: 0
                }}>
                  {me?.user?.full_name ? me.user.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '17px', letterSpacing: '-0.3px' }}>{me?.user?.full_name || 'Пользователь'}</div>
                  <div style={{ color: 'var(--text-hint)', fontSize: '13px', fontWeight: '500' }}>@{me?.user?.username || 'Без имени'}</div>
                </div>
              </div>

              {me?.profile?.has_profile && (
                <div 
                  onClick={() => {
                    if (me.profile.client_id) {
                      navigator.clipboard.writeText(me.profile.client_id);
                      showToast('Client ID скопирован', 'success');
                    }
                  }}
                  style={{ 
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
                    padding: '12px 16px', 
                    background: 'rgba(255,255,255,0.03)', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.06)',
                    cursor: me.profile.client_id ? 'pointer' : 'default',
                    transition: 'background 0.2s'
                  }}
                >
                  <div style={{ fontSize: '13px', color: 'var(--text-hint)', fontWeight: '500' }}>VPN-клиент ID</div>
                  <div style={{ 
                    fontFamily: 'monospace', fontSize: '13px', 
                    background: 'rgba(14, 165, 233, 0.1)', 
                    color: '#7DD3FC',
                    padding: '4px 10px', borderRadius: '6px',
                    border: '1px solid rgba(14, 165, 233, 0.15)',
                    display: 'flex', alignItems: 'center', gap: '6px'
                  }}>
                    {me.profile.client_id ? `${me.profile.client_id.substring(0, 8)}...` : 'Неизвестно'}
                    {me.profile.client_id && <span style={{ fontSize: '11px', opacity: 0.6 }}>📋</span>}
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
              onRevokeVpn={handleRevokeVpn}
              busy={busy === 'protocol' || busy === 'revoke'}
            />

            {/* Version & Force Refresh */}
            <div style={{ 
              marginTop: '16px', 
              textAlign: 'center', 
              fontSize: '11px', 
              color: 'var(--text-hint)',
              opacity: 0.5,
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div>Сборка v{APP_VERSION}</div>
              <div 
                onClick={() => window.location.reload(true)} 
                style={{ textDecoration: 'underline', cursor: 'pointer' }}
              >
                Проверить обновления (Hard Reload)
              </div>
            </div>
          </div>
        )}

        {activeTab === 'admin' && me?.user?.is_admin && (
          <div className="tab-pane fade-in">
            <AdminPanel onError={(msg) => showToast(msg, 'error')} onSuccess={(msg) => showToast(msg, 'success')} />
          </div>
        )}
        </Suspense>
      </div>

      <Suspense fallback={null}>
      <BottomNav activeTab={activeTab} onTabChange={setActiveTab} isAdmin={Boolean(me?.user?.is_admin)} />

      {/* Floating Support Button */}
      {me?.user && (
        <>
          <button
            className={`fab-support ${showSupport ? 'active' : ''}`}
            onClick={() => setShowSupport(!showSupport)}
            title="Поддержка"
          >
            {showSupport ? (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 11.5C21 16.1944 16.9706 20 12 20C10.6698 20 9.40702 19.7402 8.27192 19.2687C7.69766 19.0302 7.04273 18.96 6.42593 19.0881C5.16104 19.3511 4 20.1222 4 20.1222C4 20.1222 4.41738 18.6601 4.54271 17.5898C4.59371 17.1541 4.46995 16.7115 4.19793 16.3537C3.43572 15.3512 3 14.0734 3 12.6937C3 7.99933 7.02944 4.1937 12 4.1937C16.9706 4.1937 21 7.99933 21 11.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
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
      </Suspense>
    </div>
  );
}

export default App;
