import React from 'react';

const IconGlobe = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/>
  </svg>
);

const IconCheck = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0EA5E9" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="svg-check">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const IconCopy = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
);

const getFlagEmoji = (label) => {
  const match = label.match(/^([A-Z]{2})/);
  if (!match) return <IconGlobe />;
  switch (match[1]) {
    case 'FI': return '🇫🇮';
    case 'DE': return '🇩🇪';
    case 'RU': return '🇷🇺';
    case 'NL': return '🇳🇱';
    case 'US': return '🇺🇸';
    case 'TR': return '🇹🇷';
    default: return <IconGlobe />;
  }
};

const parseLabel = (raw) => {
  const match = raw.match(/^(?:[A-Z]{2}\s)?(.*?)(?:\s\((.*?)\))?$/);
  if (match) {
    return { name: match[1]?.trim() || raw, tag: match[2] || '' };
  }
  return { name: raw, tag: '' };
};

export default function ServerSelector({ endpoints, currentEndpoint, onSelect, onCopy, busy }) {
  if (!endpoints?.length) return null;

  return (
    <div className="server-list">
      {endpoints.map((ep) => {
        const parsed = parseLabel(ep.label);
        const isActive = currentEndpoint === ep.name;
        
        return (
          <button
            key={ep.name}
            className={`server-card ${isActive ? 'server-card--active' : ''}`}
            onClick={() => onSelect(ep.name)}
            disabled={busy || isActive}
          >
            <div className={`server-card__radio ${isActive ? 'server-card__radio--active' : ''}`}>
              {isActive && <IconCheck />}
            </div>
            
            <span className="server-card__icon" style={{ fontSize: '28px' }}>
              {getFlagEmoji(ep.label)}
            </span>
            
            <div className="server-card__text">
              <span className="server-card__label">
                {parsed.name}
              </span>
              <span className="server-card__desc">
                {parsed.tag ? (
                  <span className="server-card__tag">{parsed.tag}</span>
                ) : (
                  ep.description || (ep.is_relay ? 'Оптимально' : 'Прямое')
                )}
              </span>
            </div>
            
            <div className="server-card__actions">
              <div 
                className="btn-icon btn-icon--copy" 
                onClick={(e) => { e.stopPropagation(); onCopy(ep.name); }}
                title="Скопировать"
              >
                <IconCopy />
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
