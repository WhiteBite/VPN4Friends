import React from 'react';
import { IconHome, IconGlobe, IconStats, IconShield } from '../ui/Icons';



export default function BottomNav({ activeTab, onTabChange, isAdmin }) {
  return (
    <div className="bottom-nav">
      <button
        className={`nav-item ${activeTab === 'home' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('home')}
      >
        <div className="nav-icon"><IconHome /></div>
        <div className="nav-label">Главная</div>
      </button>

      <button
        className={`nav-item ${activeTab === 'locations' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('locations')}
      >
        <div className="nav-icon"><IconGlobe /></div>
        <div className="nav-label">Локации</div>
      </button>

      <button
        className={`nav-item ${activeTab === 'profile' ? 'nav-item--active' : ''}`}
        onClick={() => onTabChange('profile')}
      >
        <div className="nav-icon"><IconStats /></div>
        <div className="nav-label">Профиль</div>
      </button>

      {isAdmin && (
        <button
          className={`nav-item ${activeTab === 'admin' ? 'nav-item--active' : ''}`}
          onClick={() => onTabChange('admin')}
        >
          <div className="nav-icon"><IconShield /></div>
          <div className="nav-label">Админка</div>
        </button>
      )}
    </div>
  );
}
