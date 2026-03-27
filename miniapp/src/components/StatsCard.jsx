import React, { useState, useEffect } from 'react';
import { fetchStats } from '../api';

const IconBarChart = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
  </svg>
);

const IconUpload = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
);

const IconDownload = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);

const IconRefresh = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
  </svg>
);

export default function StatsCard({ visible, onError }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible && !stats) {
      loadStats();
    }
  }, [visible]);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (e) {
      onError?.('Не удалось загрузить статистику.');
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;

  return (
    <section className="card">
      <div className="card-title"><IconBarChart /> Статистика</div>
      {loading ? (
        <div className="skeleton-group">
          <div className="skeleton skeleton--text skeleton--text-long" />
          <div className="skeleton skeleton--text skeleton--text-short" />
        </div>
      ) : stats ? (
        <div className="stats-grid" style={{ marginBottom: '16px' }}>
          <div className="stat-item">
            <span className="stat-icon"><IconUpload /></span>
            <div className="stat-data">
              <div className="stat-value">{stats.upload_formatted}</div>
              <div className="stat-label">Загружено</div>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon"><IconDownload /></span>
            <div className="stat-data">
              <div className="stat-value">{stats.download_formatted}</div>
              <div className="stat-label">Скачано</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="muted small">Нет данных</div>
      )}
      {stats && (
        <button type="button" className="btn btn--ghost btn--full" onClick={loadStats}>
          <IconRefresh /> Обновить
        </button>
      )}
    </section>
  );
}
