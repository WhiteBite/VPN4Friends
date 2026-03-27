import React from 'react';

export default function ServerSelector({ endpoints, currentEndpoint, onSelect, busy }) {
  if (!endpoints?.length) return null;

  return (
    <div className="server-list">
      {endpoints.map((ep) => (
        <button
          key={ep.name}
          className={`server-card ${currentEndpoint === ep.name ? 'server-card--active' : ''}`}
          onClick={() => onSelect(ep.name)}
          disabled={busy || currentEndpoint === ep.name}
        >
          <span className="server-card__icon">
            {ep.is_relay ? '🔀' : '🌐'}
          </span>
          <div className="server-card__text">
            <span className="server-card__label">{ep.label}</span>
            <span className="server-card__desc">{ep.description || (ep.is_relay ? 'Оптимально' : 'Прямое')}</span>
          </div>
          {currentEndpoint === ep.name && <span className="server-card__check">✔</span>}
        </button>
      ))}
    </div>
  );
}
