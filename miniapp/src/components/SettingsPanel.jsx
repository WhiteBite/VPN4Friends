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
      {profile.available_snis?.length > 0 && (
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

      {/* Danger Zone */}
      <div style={{ borderTop: '1px solid rgba(255,100,100,0.2)', paddingTop: '16px', marginTop: '16px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-hint)', marginBottom: '12px', lineHeight: '1.4' }}>
          Если вы хотите полностью удалить свой VPN-профиль (например, устройство утеряно или ключ скомпрометирован), вы можете отозвать его. Для получения нового нужно будет отправить новую заявку.
        </div>
        <button
          onClick={() => !busy && onRevokeVpn && onRevokeVpn()}
          disabled={busy}
          style={{
            width: '100%',
            padding: '12px',
            background: 'rgba(239, 68, 68, 0.1)',
            color: '#ef4444',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            fontSize: '14px',
            fontWeight: '600',
            cursor: busy ? 'not-allowed' : 'pointer'
          }}
        >
          {busy ? 'Удаление...' : 'Отозвать VPN'}
        </button>
      </div>
    </Card>
  );
}
