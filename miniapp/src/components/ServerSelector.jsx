import React, { useState } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import Card from '../ui/Card';
import Tooltip from '../ui/Tooltip';
import { IconGlobe, IconCheck, IconCopy } from '../ui/Icons';

const getTransportTooltip = (transport, isRelay) => {
  transport = (transport || '').toLowerCase();
  if (transport === 'mtproto') return "Telegram Proxy (MTProto). Не шифрует весь трафик телефона, только для обхода блокировок в самом Telegram.";
  if (transport === 'socks' || transport === 'http') return "SOCKS5/HTTP Proxy. Подходит для прицельного обхода блокировок в браузере или отдельных программах (включая Telegram).";
  
  if (isRelay) {
    if (transport === 'grpc') return "Трафик идёт через Москву (РФ) и маскируется под gRPC (как видео-стриминг). Максимальная защита от блокировок провайдерами, но пинг чуть выше.";
    if (transport === 'tcp' || transport === 'xhttp') return "Трафик идёт через Москву. Маскируется под обычный веб-сайт (xHTTP/TCP). Умеренная защита и хороший отклик.";
    return "Трафик идёт через релейный узел (обычно в РФ) для обхода жестких блокировок.";
  }
  
  if (transport === 'vless' || transport === 'reality') return "Прямое подключение к серверу (Reality). Самая высокая скорость (идеально для YouTube), но провайдер может пытаться блокировать.";
  return "Стандартное VPN подключение.";
};
 
const getStatusColor = (status, loadLevel) => {
  if (status !== 'up') return '#F44336';
  if (loadLevel === 'high') return '#F44336';
  if (loadLevel === 'medium') return '#FFC107';
  return '#4CAF50';
};

const GROUP_INFO = {
  'fast': { title: '⚡ Для обычного использования', desc: 'Wi-Fi, домашний интернет и быстрая загрузка без потерь скорости.' },
  'warp': { title: '🎬 Видео и Соцсети (WARP)', desc: 'Обход блокировок по IP (Netflix, Instagram, ChatGPT).' },
  'stealth': { title: '🛡 Строгая блокировка (Stealth)', desc: 'Использовать, если провайдер жестко блокирует VPN. Работает медленнее обычных.' },
  'stealth_warp': { title: '🛡🎬 Stealth + WARP', desc: 'Строгий обход провайдера + доступ к западным сервисам.' },
  'moscow': { title: '📶 Для мобильного интернета', desc: 'Проходит через РФ-релей. Лучший вариант от блокировок МТС, Теле2, Мегафон и др.' }
};

export default function ServerSelector({ endpoints, currentEndpoint, onSelect, onCopy, busy, showTelegramProxies = true }) {
  const [expandedGroups, setExpandedGroups] = useState({});
  const [qrModal, setQrModal] = useState(null);

  if (!endpoints?.length) return null;

  // Group endpoints
  // category -> group -> [endpoints]
  const grouped = endpoints.reduce((acc, ep) => {
    const cat = ep.category || 'vpn';
    const grp = ep.group || 'fast';
    
    // For telegram proxies we put them all in one group
    const finalGrp = cat === 'telegram' ? 'telegram' : grp;

    if (!acc[cat]) acc[cat] = {};
    if (!acc[cat][finalGrp]) acc[cat][finalGrp] = [];
    acc[cat][finalGrp].push(ep);
    return acc;
  }, {});

  const toggleGroup = (grp) => {
    setExpandedGroups(prev => ({ ...prev, [grp]: !prev[grp] }));
  };

  const renderCategory = (categoryName, groupsMap) => {
    if (!groupsMap || Object.keys(groupsMap).length === 0) return null;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
        {categoryName !== 'vpn' && (
          <h4 style={{ margin: 0, paddingLeft: '8px', opacity: 0.8, fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '700' }}>
            ✈️ Прокси для Telegram
          </h4>
        )}

        {Object.entries(groupsMap).map(([groupId, eps]) => {
          const hasActive = eps.some(e => e.name === currentEndpoint);
          const isExpanded = expandedGroups[groupId] !== undefined ? expandedGroups[groupId] : true;
          const info = categoryName === 'telegram' 
            ? { title: 'Telegram MTProto', desc: 'Для обхода блокировок внутри Telegram' } 
            : (GROUP_INFO[groupId] || { title: `🌐 Группа ${groupId}`, desc: '' });

          return (
            <div key={groupId} style={{ 
              background: 'var(--bg-elevated)', 
              borderRadius: '16px', 
              border: `1px solid ${hasActive ? 'var(--accent)' : 'var(--border)'}`,
              overflow: 'hidden'
            }}>
              {/* Group Header */}
              <div 
                onClick={() => toggleGroup(groupId)}
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  padding: '16px',
                  cursor: 'pointer',
                  background: hasActive ? 'rgba(var(--accent-rgb), 0.05)' : 'transparent'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: info.desc ? '4px' : '0' }}>
                  <span style={{ fontWeight: '600', fontSize: '16px' }}>{info.title}</span>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {isExpanded ? 'Свернуть ▲' : eps.length + (categoryName === 'vpn' ? ' серверов ▼' : ' опции ▼')}
                  </div>
                </div>
                {info.desc && (
                  <div style={{ fontSize: '12px', color: 'var(--text-hint)' }}>{info.desc}</div>
                )}
              </div>

              {/* Endpoints List for the Group */}
              {isExpanded && (
                <div style={{ display: 'flex', flexDirection: 'column', padding: '0 8px 12px 8px', gap: '6px' }}>
                  {eps.map(ep => {
                    const isActive = currentEndpoint === ep.name;
                    return (
                      <div
                        key={ep.name}
                        onClick={() => {
                          if (ep.vpn_link) {
                            setQrModal({ name: ep.label || ep.name, link: ep.vpn_link });
                          } else {
                            onCopy(ep.name);
                          }
                        }}
                        className="server-card"
                        style={{
                          padding: '16px',
                          cursor: 'pointer',
                          marginBottom: '8px',
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          color: 'var(--text)',
                          transition: 'background 0.2s, border-color 0.2s',
                        }}
                        onMouseOver={e => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
                        }}
                        onMouseOut={e => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                        }}
                      >
                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {/* Status Indicator */}
                              <div style={{ 
                                width: '8px', 
                                height: '8px', 
                                borderRadius: '50%', 
                                background: getStatusColor(ep.status, ep.load_level),
                                boxShadow: ep.status === 'up' ? `0 0 8px ${getStatusColor(ep.status, ep.load_level)}` : 'none'
                              }} />
                              <span style={{ fontWeight: '600', fontSize: '15px', color: 'var(--text)' }}>
                                {ep.label || ep.name}
                              </span>
                              <Tooltip iconStyle={{ color: 'var(--text-hint)' }} text={getTransportTooltip(ep.transport, ep.is_relay)} />
                              <div style={{ marginLeft: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                                {ep.status === 'up' && ep.latency && (
                                  <span style={{ fontSize: '11px', opacity: 0.5, fontVariantNumeric: 'tabular-nums', fontWeight: '500' }}>
                                    {ep.latency}ms
                                  </span>
                                )}
                                {ep.status === 'up' && ep.online_count > 0 && (
                                  <span style={{ fontSize: '10px', opacity: 0.4, fontWeight: '400' }}>
                                    👥 {ep.online_count}
                                  </span>
                                )}
                              </div>
                            </div>
                            <span style={{ fontSize: '12px', color: 'var(--text-hint)', fontWeight: '500' }}>
                              {ep.country ? `Локация: ${ep.country}` : (ep.is_relay ? 'Оптимально (через МСК)' : 'Прямое к серверу')}
                            </span>
                          </div>

                        {/* Action Box */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '8px' }}>
                          {ep.vpn_link && (
                            <div 
                              onClick={(e) => { e.stopPropagation(); setQrModal({ name: ep.label || ep.name, link: ep.vpn_link }); }}
                              title="Показать QR-код"
                              style={{ 
                                padding: '10px', 
                                borderRadius: '10px', 
                                background: 'rgba(255, 255, 255, 0.05)', 
                                color: 'var(--text-hint)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                border: '1px solid rgba(255, 255, 255, 0.05)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                              }}
                              onMouseOver={e => {
                                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                                e.currentTarget.style.color = '#fff';
                              }}
                              onMouseOut={e => {
                                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                                e.currentTarget.style.color = 'var(--text-hint)';
                              }}
                            >
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                            </div>
                          )}
                          <div 
                            className="btn-icon btn-icon--copy" 
                            onClick={(e) => { e.stopPropagation(); onCopy(ep.name); }}
                            title="Скопировать ссылку"
                            style={{
                              background: 'rgba(255, 255, 255, 0.05)',
                              color: 'var(--text-hint)',
                              border: '1px solid rgba(255, 255, 255, 0.05)',
                              width: '40px', height: '40px', borderRadius: '10px',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              cursor: 'pointer',
                              transition: 'all 0.2s'
                            }}
                            onMouseOver={e => {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                              e.currentTarget.style.color = '#fff';
                            }}
                            onMouseOut={e => {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                              e.currentTarget.style.color = 'var(--text-hint)';
                            }}
                          >
                            <IconCopy />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="server-selector-container" style={{ paddingBottom: '16px' }}>
      {renderCategory('vpn', grouped['vpn'])}
      {showTelegramProxies && renderCategory('telegram', grouped['telegram'])}
      
      {qrModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(12px)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }} onClick={() => setQrModal(null)}>
          <div style={{ 
            background: 'rgba(30, 30, 35, 0.85)', 
            border: '1px solid rgba(255, 255, 255, 0.1)', 
            boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            padding: '24px', 
            borderRadius: '24px', 
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', 
            maxWidth: '320px', width: '100%', color: 'var(--text)' 
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', textAlign: 'center' }}>
              <div style={{ fontWeight: '800', fontSize: '18px', letterSpacing: '-0.3px' }}>{qrModal.name}</div>
              <p style={{ fontSize: '13px', color: 'var(--text-hint)', margin: 0, lineHeight: 1.4 }}>
                Отсканируйте камерой телефона или VPN-клиентом
              </p>
            </div>

            <div style={{ padding: '16px', background: '#fff', borderRadius: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.1)' }}>
              <QRCodeCanvas 
                id="qr-code-canvas"
                value={qrModal.link} 
                size={220}
                level="M"
                includeMargin={false}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
              <button 
                onClick={() => {
                  navigator.clipboard.writeText(qrModal.link).then(() => {
                    if (window.showToast) window.showToast('Ссылка скопирована', 'success');
                  }).catch(() => {
                    // fallback if showToast doesn't exist globally
                  });
                  setQrModal(null);
                  onCopy(qrModal.name); // Calling onCopy also shows toast usually
                }}
                style={{
                  width: '100%', padding: '14px', borderRadius: '16px', border: 'none',
                  background: 'rgba(14, 165, 233, 0.15)', color: '#7DD3FC', fontWeight: '700', fontSize: '15px',
                  cursor: 'pointer', transition: 'background 0.2s'
                }}
              >
                📋 Скопировать ссылку
              </button>

              <button 
                onClick={() => {
                  const canvas = document.getElementById("qr-code-canvas");
                  if (canvas) {
                    const url = canvas.toDataURL("image/png");
                    const link = document.createElement("a");
                    link.download = `vpn-${qrModal.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.png`;
                    link.href = url;
                    link.click();
                  }
                }}
                style={{
                  width: '100%', padding: '14px', borderRadius: '16px', border: 'none',
                  background: 'rgba(255, 255, 255, 0.08)', color: 'var(--text)', fontWeight: '600', fontSize: '14px',
                  cursor: 'pointer', transition: 'background 0.2s'
                }}
              >
                📥 Сохранить в галерею
              </button>
              
              <button 
                onClick={() => setQrModal(null)} 
                style={{ 
                  width: '100%', padding: '14px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)', 
                  background: 'transparent', color: 'var(--text-hint)', fontWeight: '600', fontSize: '14px',
                  cursor: 'pointer', transition: 'all 0.2s', marginTop: '4px'
                }}
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
