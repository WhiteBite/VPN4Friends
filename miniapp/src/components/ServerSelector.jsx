import React from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { IconGlobe, IconCheck, IconCopy } from '../ui/Icons';

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
