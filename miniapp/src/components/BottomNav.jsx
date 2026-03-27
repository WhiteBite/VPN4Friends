import React from 'react';

const IconHome = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const IconGlobe = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    <path d="M2 12h20"/>
  </svg>
);

const IconStats = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
);

export default function BottomNav({ activeTab, onTabChange }) {
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
    </div>
  );
}
