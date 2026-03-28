import React, { useState, useEffect } from 'react';
import { fetchStats } from '../api';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { IconBarChart, IconUpload, IconDownload, IconRefresh } from '../ui/Icons';

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
    <Card>
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
        <Button variant="secondary" style={{ width: '100%' }} onClick={loadStats}>
          <IconRefresh /> Обновить
        </Button>
      )}
    </Card>
  );
}
