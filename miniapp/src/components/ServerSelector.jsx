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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        <h4 style={{ margin: 0, paddingLeft: '8px', opacity: 0.8, fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {categoryName === 'vpn' ? '📍 Выбор отдельного сервера' : '✈️ Прокси для Telegram'}
        </h4>

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
                        onClick={() => categoryName === 'vpn' ? onSelect(ep.name) : onCopy(ep.name)}
                        className={`server-card ${isActive ? 'server-card--active' : ''}`}
                        style={{
                          padding: '16px',
                          cursor: (busy && categoryName === 'vpn') ? 'not-allowed' : 'pointer',
                          opacity: (busy && !isActive && categoryName === 'vpn') ? 0.6 : 1,
                          marginBottom: '8px',
                          background: isActive ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.8), rgba(5, 150, 105, 0.9))' : 'rgba(255, 255, 255, 0.03)',
                          border: isActive ? '1px solid rgba(16, 185, 129, 0.5)' : '1px solid rgba(255, 255, 255, 0.08)',
                          color: isActive ? '#fff' : 'var(--text)',
                          boxShadow: isActive ? '0 8px 24px rgba(16, 185, 129, 0.25), inset 0 1px 1px rgba(255, 255, 255, 0.2)' : 'none',
                        }}
                      >
                        {categoryName === 'vpn' && (
                          <div className={`server-card__radio ${isActive ? 'server-card__radio--active' : ''}`} style={{ borderColor: isActive ? '#fff' : 'rgba(255,255,255,0.2)', background: isActive ? 'rgba(255,255,255,0.2)' : 'transparent' }}>
                            {isActive && <IconCheck style={{ color: '#fff' }} />}
                          </div>
                        )}
                        
                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {/* Status Indicator */}
                              <div style={{ 
                                width: '8px', 
                                height: '8px', 
                                borderRadius: '50%', 
                                background: ep.status === 'up' ? (isActive ? '#fff' : '#4CAF50') : (ep.status === 'down' ? '#F44336' : '#9E9E9E'),
                                boxShadow: isActive ? '0 0 8px rgba(255,255,255,0.8)' : 'none'
                              }} />
                              <span style={{ fontWeight: isActive ? '700' : '600', fontSize: '15px', color: isActive ? '#fff' : 'var(--text)' }}>
                                {ep.label || ep.name}
                              </span>
                              <Tooltip iconStyle={{ color: isActive ? 'rgba(255,255,255,0.7)' : 'var(--text-hint)' }} text={getTransportTooltip(ep.transport, ep.is_relay)} />
                              {ep.status === 'up' && ep.latency && (
                                <span style={{ fontSize: '11px', opacity: isActive ? 0.9 : 0.5, marginLeft: 'auto', fontVariantNumeric: 'tabular-nums', fontWeight: '500' }}>
                                  {ep.latency}ms
                                </span>
                              )}
                            </div>
                            <span style={{ fontSize: '12px', color: isActive ? 'rgba(255,255,255,0.8)' : 'var(--text-hint)', fontWeight: '500' }}>
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
                                background: isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)', 
                                color: isActive ? '#fff' : 'var(--text-hint)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                border: isActive ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid rgba(255, 255, 255, 0.05)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                              }}
                              onMouseOver={e => e.currentTarget.style.background = isActive ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)'}
                              onMouseOut={e => e.currentTarget.style.background = isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)'}
                            >
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                            </div>
                          )}
                          <div 
                            className="btn-icon btn-icon--copy" 
                            onClick={(e) => { e.stopPropagation(); onCopy(ep.name); }}
                            title="Скопировать ссылку"
                            style={{
                              background: isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                              color: isActive ? '#fff' : 'var(--text-hint)',
                              border: isActive ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid rgba(255, 255, 255, 0.05)',
                              width: '40px', height: '40px', borderRadius: '10px'
                            }}
                            onMouseOver={e => e.currentTarget.style.background = isActive ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)'}
                            onMouseOut={e => e.currentTarget.style.background = isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)'}
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
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }} onClick={() => setQrModal(null)}>
          <div style={{ background: '#fff', padding: '24px', borderRadius: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', maxWidth: '300px', width: '100%', color: '#000' }} onClick={e => e.stopPropagation()}>
            <div style={{ fontWeight: '700', fontSize: '18px', textAlign: 'center' }}>{qrModal.name}</div>
            <p style={{ fontSize: '12px', color: '#666', textAlign: 'center', margin: 0 }}>
              Отсканируйте камерой телефона или VPN-клиентом
            </p>

            <div style={{ padding: '12px', background: '#fff', borderRadius: '16px', border: '1px solid #eee' }}>
              <QRCodeCanvas 
                id="qr-code-canvas"
                value={qrModal.link} 
                size={200}
                level="M"
                includeMargin={true}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
              <button 
                onClick={() => {
                  const canvas = document.getElementById("qr-code-canvas");
                  if (canvas) {
                    const url = canvas.toDataURL("image/png");
                    const link = document.createElement("a");
                    link.download = `vpn-${qrModal.name}.png`;
                    link.href = url;
                    link.click();
                  }
                }}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '12px',
                  border: 'none',
                  background: 'var(--accent, #ffd900)',
                  color: '#000',
                  fontWeight: '700',
                  cursor: 'pointer'
                }}
              >
                📥 Сохранить в галерею
              </button>
              
              <button 
                onClick={() => setQrModal(null)} 
                style={{ 
                  width: '100%', 
                  padding: '12px', 
                  borderRadius: '12px', 
                  border: '1px solid #eee', 
                  background: '#f5f5f5', 
                  fontWeight: '600', 
                  cursor: 'pointer' 
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
