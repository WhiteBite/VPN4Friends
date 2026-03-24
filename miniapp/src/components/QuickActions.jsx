import React from 'react';

export default function QuickActions({ onCopy, onQR, onStats, hasProfile }) {
  if (!hasProfile) return null;

  return (
    <div className="quick-actions">
      <button type="button" className="quick-action" onClick={onCopy} title="Скопировать ссылку">
        <span className="quick-action__icon">📋</span>
        <span className="quick-action__label">Скопировать</span>
      </button>
      <button type="button" className="quick-action" onClick={onQR} title="QR-код">
        <span className="quick-action__icon">📱</span>
        <span className="quick-action__label">QR-код</span>
      </button>
      <button type="button" className="quick-action" onClick={onStats} title="Статистика">
        <span className="quick-action__icon">📊</span>
        <span className="quick-action__label">Статистика</span>
      </button>
    </div>
  );
}
