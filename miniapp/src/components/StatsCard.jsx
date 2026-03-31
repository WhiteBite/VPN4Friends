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
      <div className="card-title">📊 Статистика</div>
      {loading ? (
        <div className="skeleton-group">
          <div className="skeleton skeleton--text skeleton--text-long" />
          <div className="skeleton skeleton--text skeleton--text-short" />
        </div>
      ) : stats ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
          <div style={{ 
            padding: '16px', 
            background: 'rgba(16, 185, 129, 0.06)', 
            border: '1px solid rgba(16, 185, 129, 0.12)', 
            borderRadius: '16px',
            display: 'flex', alignItems: 'center', gap: '12px'
          }}>
            <div style={{ 
              width: '36px', height: '36px', borderRadius: '10px', 
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.05))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '16px'
            }}>⬆️</div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '16px', letterSpacing: '-0.3px' }}>{stats.upload_formatted}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.3px' }}>Загружено</div>
            </div>
          </div>
          <div style={{ 
            padding: '16px', 
            background: 'rgba(59, 130, 246, 0.06)', 
            border: '1px solid rgba(59, 130, 246, 0.12)', 
            borderRadius: '16px',
            display: 'flex', alignItems: 'center', gap: '12px'
          }}>
            <div style={{ 
              width: '36px', height: '36px', borderRadius: '10px', 
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.05))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '16px'
            }}>⬇️</div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '16px', letterSpacing: '-0.3px' }}>{stats.download_formatted}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.3px' }}>Скачано</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="muted small">Нет данных</div>
      )}
      {stats && (
        <button 
          onClick={loadStats}
          style={{
            width: '100%', padding: '12px', borderRadius: '12px',
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            color: 'var(--text-hint)', fontSize: '14px', fontWeight: '600',
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            transition: 'all 0.2s'
          }}
        >
          ↻ Обновить
        </button>
      )}
    </Card>
  );
}
