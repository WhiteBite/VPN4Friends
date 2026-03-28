import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Tooltip from '../ui/Tooltip';
import { IconGlobe, IconCheck, IconCopy } from '../ui/Icons';

const getFlagEmoji = (label, country) => {
  const t = label.toUpperCase() + " " + (country || '').toUpperCase();
  if (t.includes('FI') || t.includes('ФИН')) return '🇫🇮';
  if (t.includes('DE') || t.includes('ГЕР')) return '🇩🇪';
  if (t.includes('RU') || t.includes('РОС') || t.includes('МОС')) return '🇷🇺';
  if (t.includes('NL') || t.includes('НИД')) return '🇳🇱';
  if (t.includes('US') || t.includes('США')) return '🇺🇸';
  if (t.includes('TR') || t.includes('ТУР')) return '🇹🇷';
  return <IconGlobe />;
};

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

export default function ServerSelector({ endpoints, currentEndpoint, onSelect, onCopy, busy, showTelegramProxies = true }) {
  const [expandedCountries, setExpandedCountries] = useState({});

  if (!endpoints?.length) return null;

  // Group endpoints
  // category -> country -> [endpoints]
  const grouped = endpoints.reduce((acc, ep) => {
    const cat = ep.category || 'vpn';
    const cntry = ep.country || 'Unknown';
    if (!acc[cat]) acc[cat] = {};
    if (!acc[cat][cntry]) acc[cat][cntry] = [];
    acc[cat][cntry].push(ep);
    return acc;
  }, {});

  const toggleCountry = (country) => {
    setExpandedCountries(prev => ({ ...prev, [country]: !prev[country] }));
  };

  const renderGroup = (categoryName, countriesMap) => {
    if (!countriesMap || Object.keys(countriesMap).length === 0) return null;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        <h4 style={{ margin: 0, paddingLeft: '8px', opacity: 0.8, fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {categoryName === 'vpn' ? '📶 VPN Локации' : '✈️ Прокси для Telegram'}
        </h4>

        {Object.entries(countriesMap).map(([countryName, eps]) => {
          // Check if any endpoint in this country is currently active
          const hasActive = eps.some(e => e.name === currentEndpoint);
          // Auto-expand if active, otherwise use state. Default to true if not set to avoid hiding everything initially.
          const isExpanded = expandedCountries[countryName] !== undefined ? expandedCountries[countryName] : true;

          return (
            <div key={countryName} style={{ 
              background: 'var(--bg-elevated)', 
              borderRadius: '16px', 
              border: `1px solid ${hasActive ? 'var(--accent)' : 'var(--border)'}`,
              overflow: 'hidden'
            }}>
              {/* Country Header */}
              <div 
                onClick={() => toggleCountry(countryName)}
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  padding: '16px',
                  cursor: 'pointer',
                  background: hasActive ? 'rgba(var(--accent-rgb), 0.05)' : 'transparent'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '28px' }}>{getFlagEmoji(countryName, countryName)}</span>
                  <span style={{ fontWeight: '600', fontSize: '16px' }}>{countryName}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {isExpanded ? 'Свернуть ▲' : eps.length + (categoryName === 'vpn' ? ' опций ▼' : ' опции ▼')}
                </div>
              </div>

              {/* Endpoints List for the Country */}
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
                            {ep.description || (ep.is_relay ? 'Оптимально (через МСК)' : 'Прямое к серверу')}
                          </span>
                        </div>

                        {/* Copy Link Button (always visible for Telegram, otherwise an action icon) */}
                        <div 
                          className="btn-icon btn-icon--copy" 
                          onClick={(e) => { e.stopPropagation(); onCopy(ep.name); }}
                          title={categoryName === 'vpn' ? "Скопировать VPN ссылку" : "Скопировать Proxy ссылку"}
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
      {renderGroup('vpn', grouped['vpn'])}
      {showTelegramProxies && renderGroup('telegram', grouped['telegram'])}
    </div>
  );
}
