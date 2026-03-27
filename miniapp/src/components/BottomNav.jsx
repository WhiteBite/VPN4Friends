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
        className={`nav-item ${activeTab === 'locations' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('locations')}
      >
        <div className="nav-icon">🌍</div>
        <div className="nav-label">Локации</div>
      </button>

      <button
        className={`nav-item ${activeTab === 'profile' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('profile')}
      >
        <div className="nav-icon">📊</div>
        <div className="nav-label">Профиль</div>
      </button>
    </div>
  );
}
