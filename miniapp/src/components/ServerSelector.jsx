import React, { useState } from 'react';
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
  'fast': { title: '⚡ Обычный интернет (Direct)', desc: 'Максимальная скорость. Для ежедневного использования.' },
  'warp': { title: '🎬 Видео и Соцсети (WARP)', desc: 'Обход блокировок по IP (Netflix, Instagram, ChatGPT).' },
  'stealth': { title: '🛡 Строгая блокировка (Stealth)', desc: 'Использовать, если провайдер жестко блокирует VPN. Работает медленнее обычных.' },
  'stealth_warp': { title: '🛡🎬 Stealth + WARP', desc: 'Строгий обход провайдера + доступ к западным сервисам.' },
  'moscow': { title: '🇷🇺 Базовые (Москва)', desc: 'Точка входа в РФ.' }
};

export default function ServerSelector({ endpoints, currentEndpoint, onSelect, onCopy, busy, showTelegramProxies = true }) {
  const [expandedGroups, setExpandedGroups] = useState({});

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
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '12px',
                          borderRadius: '12px',
                          background: isActive ? 'var(--accent)' : 'var(--bg-color)',
                          color: isActive ? '#000' : 'var(--text)',
                          cursor: (busy && categoryName === 'vpn') ? 'not-allowed' : 'pointer',
                          gap: '12px',
                          opacity: (busy && !isActive && categoryName === 'vpn') ? 0.6 : 1,
                          transition: 'all 0.2s',
                          border: isActive ? 'none' : '1px solid var(--border)'
                        }}
                      >
                        {categoryName === 'vpn' && (
                          <div className={`server-card__radio ${isActive ? 'server-card__radio--active' : ''}`}>
                            {isActive && <IconCheck />}
                          </div>
                        )}
                        
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontWeight: isActive ? '700' : '500', fontSize: '15px' }}>
                              {ep.label || ep.name}
                            </span>
                            <Tooltip text={getTransportTooltip(ep.transport, ep.is_relay)} />
                          </div>
                          <span style={{ fontSize: '12px', opacity: isActive ? 0.8 : 0.6 }}>
                            {ep.country ? `Локация: ${ep.country}` : (ep.is_relay ? 'Оптимально (через МСК)' : 'Прямое к серверу')}
                          </span>
                        </div>

                        {/* Action Box: we have copy for both vpn or telegram proxies */}
                        <div 
                          className="btn-icon btn-icon--copy" 
                          onClick={(e) => { e.stopPropagation(); onCopy(ep.name); }}
                          title="Скопировать ссылку"
                          style={{
                            background: isActive ? 'rgba(0,0,0,0.1)' : 'var(--bg-elevated)',
                            color: isActive ? '#000' : 'var(--text)'
                          }}
                        >
                          <IconCopy />
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
    </div>
  );
}
