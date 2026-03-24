import React from 'react';

export default function ConnectionCard({ profile, endpoint, onCopy, link }) {
  const hasProfile = profile?.has_profile;
  const protocol = profile?.protocol?.toUpperCase() || '—';
  const label = profile?.label || protocol;

  if (!hasProfile) {
    return (
      <section className="card card--hero">
        <div className="empty-state">
          <div className="empty-icon">🔐</div>
          <div className="empty-title">Нет VPN</div>
          <div className="empty-text">
            Запроси доступ у бота — после одобрения здесь появится ссылка
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="card card--hero">
      <div className="hero-status">
        <span className="hero-protocol">{label}</span>
      </div>

      {/* Relay visualization (only if relay endpoint) */}
      {endpoint?.is_relay && (
        <div className="relay-chain">
          <span className="relay-node">🇷🇺 Москва</span>
          <span className="relay-line" />
          <span className="relay-node">🇳🇱 NL</span>
        </div>
      )}

      {/* VPN Link */}
      {link && (
        <>
          <div className="link-box" onClick={onCopy}>
            <div className="link-box__text">{link}</div>
          </div>
          <div className="link-box__hint">
            Вставь в v2rayN, Hiddify или Streisand
          </div>
          <button className="btn-copy-main" onClick={onCopy}>
            📋 Скопировать ссылку
          </button>
        </>
      )}
    </section>
  );
}
