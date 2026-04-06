import React from 'react';
import Card from '../ui/Card';
import Skeleton from '../ui/Skeleton';
import { getTelegram } from '../telegram';

export default function SettingsPanel({
  visible,
  profile,
  protocols,
  onSwitchProtocol,
  onRevokeVpn,
  busy,
}) {
  if (!visible || !profile?.has_profile) return null;

  const sortedProtocols = protocols
    ? [...protocols].sort((a, b) => Number(b.recommended) - Number(a.recommended))
    : [];

  return (
    <Card>
      <div className="card-title">⚙️ Настройки</div>

      {/* Protocol Selection */}
      <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text)', marginTop: '12px', marginBottom: '4px' }}>
        Протокол
      </div>
      
      {!protocols || protocols.length === 0 ? (
        <div className="chips-row" style={{ marginBottom: '12px', marginTop: '8px' }}>
          <Skeleton type="text" width="80px" height="32px" style={{ borderRadius: '100px' }} />
          <Skeleton type="text" width="100px" height="32px" style={{ borderRadius: '100px' }} />
          <Skeleton type="text" width="70px" height="32px" style={{ borderRadius: '100px' }} />
        </div>
      ) : (
        <>
          <div style={{ fontSize: '11px', color: 'var(--text-hint)', marginBottom: '12px' }}>
            Выберите способ подключения. Рекомендуемые отмечены ⭐
          </div>
          <div className="chips-row" style={{ marginBottom: '12px' }}>
            {sortedProtocols.map((p) => {
              const isActive = profile.protocol === p.name;
              return (
                <button
                  key={p.name}
                  type="button"
                  className={`chip ${isActive ? 'chip--active' : ''}`}
                  onClick={() => !busy && !isActive && onSwitchProtocol(p.name)}
                  disabled={busy}
                  style={{
                    opacity: busy && !isActive ? 0.5 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  {p.icon && <span>{p.icon}</span>}
                  {p.label}
                  {p.recommended && !isActive && <span style={{ fontSize: '10px', opacity: 0.8 }}>⭐</span>}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Dynamic description from server */}
      {sortedProtocols.find(p => p.name === profile.protocol)?.description && (
            <div style={{ 
              fontSize: '11px', 
              color: 'var(--text-hint)', 
              marginBottom: '20px',
              padding: '8px 12px',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              {sortedProtocols.find(p => p.name === profile.protocol).description}
            </div>
          )}

      {/* Danger Zone — subtle, not aggressive */}
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <button
          onClick={() => {
            const msg = "⚠️ Вы уверены, что хотите полностью удалить свой VPN? Это действие необратимо.";
            const tg = getTelegram();
            if (tg && tg.showConfirm) {
              tg.showConfirm(msg, (confirmed) => {
                if (confirmed) onRevokeVpn();
              });
            } else {
              if (window.confirm(msg)) {
                onRevokeVpn();
              }
            }
          }}
          disabled={busy}
          style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.15)',
            color: '#F87171',
            fontSize: '14px',
            fontWeight: '600',
            padding: '14px 16px',
            borderRadius: '12px',
            width: '100%',
            cursor: 'pointer',
            textAlign: 'center',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            transition: 'all 0.2s',
            opacity: busy ? 0.5 : 1
          }}
        >
          {busy ? '⏳ Удаление...' : '🗑️ Удалить VPN'}
        </button>
      </div>
    </Card>
  );
}
