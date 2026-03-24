import React, { useState, useEffect } from 'react';
import { fetchStats } from '../api';

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
      <div className="card-title">📊 Статистика</div>
      {loading ? (
        <div className="skeleton-group">
          <div className="skeleton skeleton--text skeleton--text-long" />
          <div className="skeleton skeleton--text skeleton--text-short" />
        </div>
      ) : stats ? (
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-icon">🔼</span>
            <div className="stat-data">
              <div className="stat-value">{stats.upload_formatted}</div>
              <div className="stat-label">Загружено</div>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">🔽</span>
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
          🔄 Обновить
        </button>
      )}
    </section>
  );
}
