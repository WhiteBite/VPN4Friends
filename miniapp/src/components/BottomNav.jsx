import React from 'react';

export default function BottomNav({ activeTab, onTabChange }) {
  return (
    <div className="bottom-nav">
      <button
        className={`nav-item ${activeTab === 'home' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('home')}
      >
        <div className="nav-icon">🏠</div>
        <div className="nav-label">Главная</div>
      </button>

      <button
        className={`nav-item ${activeTab === 'stats' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('stats')}
      >
        <div className="nav-icon">📊</div>
        <div className="nav-label">Статистика</div>
      </button>

      <button
        className={`nav-item ${activeTab === 'settings' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('settings')}
      >
        <div className="nav-icon">⚙️</div>
        <div className="nav-label">Настройки</div>
      </button>
    </div>
  );
}
