import React from 'react';
import { QRCodeSVG } from 'qrcode.react';

const IconLock = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const IconCopy = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const IconCheckCircle = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);

export default function ConnectionCard({ profile, endpoint, onCopy, link }) {
  const hasProfile = profile?.has_profile;

  if (!hasProfile) {
    return (
      <section className="card card--hero">
        <div className="empty-state">
          <div className="empty-icon"><IconLock /></div>
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
        <span className="hero-protocol">
          <IconCheckCircle /> Готов к работе
        </span>
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
            <span className="btn-icon"><IconCopy /></span>
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
