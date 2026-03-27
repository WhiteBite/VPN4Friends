import React from 'react';
import { QRCodeSVG } from 'qrcode.react';

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
            Запроси доступ у бота — после одобрения здесь появится QR-код
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

      {/* Relay visualization */}
      {endpoint?.is_relay && (
        <div className="relay-chain">
          <span className="relay-node">🇷🇺 Москва</span>
          <span className="relay-line" />
          <span className="relay-node">🇳🇱 NL</span>
        </div>
      )}

      {/* Big QR Code & Action */}
      {link ? (
        <div className="hero-action-area">
          <div className="qr-box">
             <QRCodeSVG
                value={link}
                size={180}
                bgColor="transparent"
                fgColor="#090B0F"
                level="M"
                includeMargin={false}
              />
          </div>
          <div className="qr-hint">Отсканируй или нажми "Скопировать" ↓</div>
          
          <button className="btn-copy-main" onClick={onCopy}>
            <span className="btn-icon">📋</span>
            Скопировать ссылку
          </button>
        </div>
      ) : (
        <div className="hero-action-area">
          <div className="skeleton skeleton--box" style={{ height: 180, width: 180, margin: '0 auto 16px', borderRadius: '16px' }}></div>
          <div className="skeleton skeleton--box" style={{ height: 48, borderRadius: '12px' }}></div>
        </div>
      )}
    </section>
  );
}
