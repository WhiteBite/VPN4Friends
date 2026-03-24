import React from 'react';

export default function ServerSelector({ endpoints, currentEndpoint, onSelect, busy }) {
  if (!endpoints?.length) return null;

  return (
    <section className="card">
      <div className="section-title">Точка входа</div>
      <div className="server-scroll">
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
            <span className="server-card__label">{ep.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
