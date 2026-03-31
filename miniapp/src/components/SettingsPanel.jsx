import React from 'react';
import Card from '../ui/Card';
import { getTelegram } from '../telegram';

export default function SettingsPanel({
  visible,
  profile,
  protocols,
  onSwitchProtocol,
  onUpdateSni,
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
      {sortedProtocols.length > 1 && (
        <>
          <div className="section-title" style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            Протокол
            <span data-tooltip="Разные протоколы обхода блокировок. Выбирайте VLESS по умолчанию." style={{ color: 'var(--text-hint)', cursor: 'help' }}>ℹ️</span>
          </div>
          <div className="chips-row" style={{ marginBottom: '24px', marginTop: '12px' }}>
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
                    opacity: busy && !isActive ? 0.5 : 1
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* SNI Selection */}
      {profile.available_snis?.length > 1 && (
        <>
          <div className="section-title" style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            SNI маскировка 
            <span data-tooltip="Маскировка трафика под другие сайты для обхода блокировок" style={{ color: 'var(--text-hint)', cursor: 'help' }}>ℹ️</span>
          </div>
          <div className="chips-row" style={{ marginBottom: '24px', marginTop: '12px' }}>
            {profile.available_snis.map((sni) => {
              const isActive = profile.sni === sni;
              return (
                <button
                  key={sni}
                  type="button"
                  className={`chip ${isActive ? 'chip--active' : ''}`}
                  onClick={() => !busy && !isActive && onUpdateSni(sni)}
                  disabled={busy}
                  style={{
                    opacity: busy && !isActive ? 0.5 : 1
                  }}
                >
                  {sni}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Compact Danger Zone */}
      <div style={{ marginTop: '24px' }}>
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
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#EF4444',
            fontSize: '14px',
            fontWeight: '600',
            padding: '12px 16px',
            borderRadius: '12px',
            width: '100%',
            cursor: 'pointer',
            textAlign: 'center',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            transition: 'all 0.2s',
          }}
        >
          <span style={{ fontSize: '18px' }}>🗑️</span>
          {busy ? 'Удаление...' : 'Отозвать доступ (Удалить VPN)'}
        </button>
      </div>
    </Card>
  );
}
