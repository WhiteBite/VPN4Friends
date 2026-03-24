import React from 'react';

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
    <section className="card">
      <div className="card-title">⚙️ Настройки</div>

      {/* Protocol Selection */}
      <div className="section-title">Протокол</div>
      <div className="chips-row">
        {sortedProtocols.map((p) => {
          const isActive = profile.protocol === p.name;
          return (
            <button
              key={p.name}
              type="button"
              className={`chip ${isActive ? 'chip--active' : ''}`}
              onClick={() => !busy && !isActive && onSwitchProtocol(p.name)}
              disabled={busy || isActive}
            >
              {p.label || p.name.toUpperCase()}
            </button>
          );
        })}
      </div>

      {/* SNI Selection */}
      {profile.available_snis?.length > 0 && (
        <>
          <div className="section-title">SNI маскировка</div>
          <div className="chips-row">
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
    </section>
  );
}
