import React from 'react';
import Card from '../ui/Card';

export default function SettingsPanel({
  visible,
  profile,
  protocols,
  onSwitchProtocol,
  onUpdateSni,
  busy,
}) {
  if (!visible || !profile?.has_profile) return null;

  const sortedProtocols = protocols
    ? [...protocols].sort((a, b) => Number(b.recommended) - Number(a.recommended))
    : [];

  return (
    <Card>
      <div className="card-title">⚙️ Настройки</div>

      {/* SNI Selection */}
      {profile.available_snis?.length > 1 && (
        <>
          <div className="section-title" style={{ marginTop: '16px' }}>SNI маскировка</div>
          <div className="chips-row" style={{ marginBottom: '24px' }}>
            {profile.available_snis.map((sni) => {
              const isActive = profile.sni === sni;
              return (
                <button
                  key={sni}
                  type="button"
                  className={`chip ${isActive ? 'chip--active' : ''}`}
                  onClick={() => !busy && !isActive && onUpdateSni(sni)}
                  disabled={busy || isActive}
                >
                  {sni}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Compact Danger Zone */}
      <div style={{ marginTop: '24px', borderTop: '1px dotted var(--border)' }}>
        <button
          onClick={() => {
            if (window.confirm("⚠️ Вы уверены, что хотите полностью удалить свой VPN? Это действие необратимо.")) {
              onRevokeVpn();
            }
          }}
          disabled={busy}
          style={{
            background: 'none',
            border: 'none',
            color: 'rgba(239, 68, 68, 0.6)',
            fontSize: '13px',
            padding: '12px 0',
            width: '100%',
            cursor: 'pointer',
            textAlign: 'center'
          }}
        >
          {busy ? 'Удаление...' : 'Отозвать доступ'}
        </button>
      </div>
    </Card>
  );
}
