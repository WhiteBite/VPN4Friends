import React, { useEffect, useState } from 'react';
import {
  fetchMe,
  fetchProtocols,
  switchProtocol,
  updateSni,
  createPreset,
  deletePreset,
  getPresetConfig,
} from './api';
import { getTelegram } from './telegram';

function Loading() {
  return (
    <div className="center-text muted">
      Загрузка...
    </div>
  );
}

function ErrorBanner({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="banner banner-error">
      <span>{message}</span>
      {onClose && (
        <button className="icon-button" type="button" onClick={onClose}>
          ×
        </button>
      )}
    </div>
  );
}

function InfoBanner({ message }) {
  if (!message) return null;
  return <div className="banner banner-info">{message}</div>;
}

function ProtocolChips({ current, protocols, onSwitch, busy }) {
  if (!protocols || protocols.length === 0) {
    return <div className="muted small">Протоколы ещё не настроены.</div>;
  }

  const sorted = [...protocols].sort((a, b) => Number(b.recommended) - Number(a.recommended));

  return (
    <div className="chips-row">
      {sorted.map((p) => {
        const isActive = current === p.name;
        return (
          <button
            key={p.name}
            type="button"
            className={`chip ${isActive ? 'chip-active' : ''}`}
            onClick={() => !busy && !isActive && onSwitch(p.name)}
            disabled={busy || isActive}
          >
            {p.label || p.name.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}

function SniSelector({ current, options, onSelect, busy }) {
  if (!options || options.length === 0) {
    return <div className="muted small">SNI для этого протокола не настраивается.</div>;
  }

  return (
    <div className="chips-row">
      {options.map((sni) => {
        const isActive = current === sni;
        return (
          <button
            key={sni}
            type="button"
            className={`chip ${isActive ? 'chip-active' : ''}`}
            onClick={() => !busy && !isActive && onSelect(sni)}
            disabled={busy || isActive}
          >
            {sni}
          </button>
        );
      })}
    </div>
  );
}

function PresetForm({ onCreate, busy }) {
  const [name, setName] = useState('Мой пресет');
  const [appType, setAppType] = useState('v2ray');
  const [format, setFormat] = useState('vless_uri');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onCreate({ name: name.trim(), app_type: appType, format, options: {} });
  };

  return (
    <form className="preset-form" onSubmit={handleSubmit}>
      <div className="field-group">
        <label className="label" htmlFor="preset-name">
          Название
        </label>
        <input
          id="preset-name"
          className="input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={busy}
        />
      </div>
      <div className="field-row">
        <div className="field">
          <label className="label" htmlFor="preset-app">
            Приложение
          </label>
          <select
            id="preset-app"
            className="input"
            value={appType}
            onChange={(e) => setAppType(e.target.value)}
            disabled={busy}
          >
            <option value="v2ray">V2RayNG / Nekobox</option>
            <option value="clash">Clash / Hiddify</option>
          </select>
        </div>
        <div className="field">
          <label className="label" htmlFor="preset-format">
            Формат
          </label>
          <select
            id="preset-format"
            className="input"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            disabled={busy}
          >
            <option value="vless_uri">VPN URI</option>
          </select>
        </div>
      </div>
      <button className="button button-primary" type="submit" disabled={busy}>
        Создать пресет
      </button>
    </form>
  );
}

function App() {
  const [colorScheme, setColorScheme] = useState('dark');
  const [initialLoading, setInitialLoading] = useState(true);
  const [me, setMe] = useState(null);
  const [protocols, setProtocols] = useState([]);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busyAction, setBusyAction] = useState('');
  const [presetPreview, setPresetPreview] = useState(null);

  useEffect(() => {
    const tg = getTelegram();
    if (tg) {
      try {
        tg.ready();
        tg.expand();
      } catch (e) {
        // ignore
      }
      if (tg.colorScheme) {
        setColorScheme(tg.colorScheme);
      }
    }

    const load = async () => {
      try {
        const [data, protocolList] = await Promise.all([fetchMe(), fetchProtocols()]);
        setMe(data);
        setProtocols(protocolList);
      } catch (e) {
        setError('Не удалось загрузить данные. Попробуй открыть мини-апп ещё раз.');
      } finally {
        setInitialLoading(false);
      }
    };

    load();
  }, []);

  const refreshMe = async () => {
    try {
      const data = await fetchMe();
      setMe(data);
    } catch (e) {
      setError('Ошибка обновления данных.');
    }
  };

  const handleSwitchProtocol = async (protocol) => {
    setError('');
    setInfo('');
    setBusyAction('protocol');
    try {
      await switchProtocol(protocol);
      await refreshMe();
      setInfo('Протокол переключён. Обнови профиль в приложении.');
    } catch (e) {
      setError('Не удалось переключить протокол.');
    } finally {
      setBusyAction('');
    }
  };

  const handleUpdateSni = async (sni) => {
    setError('');
    setInfo('');
    setBusyAction('sni');
    try {
      await updateSni(sni);
      await refreshMe();
      setInfo('SNI обновлён. Сгенерируй новый пресет для приложений.');
    } catch (e) {
      setError('Не удалось обновить SNI.');
    } finally {
      setBusyAction('');
    }
  };

  const handleCreatePreset = async (payload) => {
    setError('');
    setInfo('');
    setBusyAction('create-preset');
    try {
      await createPreset(payload);
      await refreshMe();
      setInfo('Пресет создан. Открой его, чтобы скопировать конфиг.');
    } catch (e) {
      setError('Не удалось создать пресет.');
    } finally {
      setBusyAction('');
    }
  };

  const handleDeletePreset = async (id) => {
    if (!window.confirm('Удалить этот пресет?')) return;
    setError('');
    setInfo('');
    setBusyAction(`delete-${id}`);
    try {
      await deletePreset(id);
      await refreshMe();
      setInfo('Пресет удалён.');
      if (presetPreview && presetPreview.id === id) {
        setPresetPreview(null);
      }
    } catch (e) {
      setError('Не удалось удалить пресет.');
    } finally {
      setBusyAction('');
    }
  };

  const handleOpenPreset = async (preset) => {
    setError('');
    setInfo('');
    setBusyAction(`open-${preset.id}`);
    try {
      const config = await getPresetConfig(preset.id);
      setPresetPreview({ id: preset.id, name: preset.name, config });
    } catch (e) {
      setError('Не удалось получить конфиг пресета.');
    } finally {
      setBusyAction('');
    }
  };

  const handleCopyConfig = async () => {
    if (!presetPreview) return;
    try {
      await navigator.clipboard.writeText(presetPreview.config.value);
      setInfo('Ссылка скопирована в буфер.');
    } catch (e) {
      setError('Не удалось скопировать в буфер обмена.');
    }
  };

  if (initialLoading) {
    return (
      <div className="app" data-theme={colorScheme}>
        <Loading />
      </div>
    );
  }

  if (!me) {
    return (
      <div className="app" data-theme={colorScheme}>
        <ErrorBanner message={error || 'Не удалось загрузить мини-апп.'} />
      </div>
    );
  }

  const { user, profile, presets } = me;

  return (
    <div className="app" data-theme={colorScheme}>
      <header className="header">
        <div className="title">VPN4Friends</div>
        <div className="subtitle">Твой умный VPN-кабинет</div>
      </header>

      <ErrorBanner message={error} onClose={() => setError('')} />
      <InfoBanner message={info} />

      <section className="card">
        <div className="card-title">Привет, {user.full_name} 👋</div>
        {user.username && <div className="muted small">@{user.username}</div>}
      </section>

      <section className="card">
        <div className="card-title">Текущий VPN</div>
        {!profile.has_profile ? (
          <div className="muted">
            У тебя ещё нет активного VPN-профиля.
            <br />
            Получи доступ через бота и вернись в мини-апп.
          </div>
        ) : (
          <>
            <div className="info-row">
              <span className="label">Протокол</span>
              <span className="value">{profile.protocol?.toUpperCase()}</span>
            </div>
            {profile.label && (
              <div className="info-row">
                <span className="label">Метка</span>
                <span className="value">{profile.label}</span>
              </div>
            )}
            <div className="section-title">Переключить протокол</div>
            <ProtocolChips
              current={profile.protocol}
              protocols={protocols}
              onSwitch={handleSwitchProtocol}
              busy={busyAction === 'protocol'}
            />

            <div className="section-title">Выбрать SNI</div>
            <SniSelector
              current={profile.sni}
              options={profile.available_snis}
              onSelect={handleUpdateSni}
              busy={busyAction === 'sni'}
            />
          </>
        )}
      </section>

      <section className="card">
        <div className="card-title">Пресеты подключения</div>
        {!profile.has_profile ? (
          <div className="muted small">
            Сначала получи VPN-профиль, чтобы создавать пресеты.
          </div>
        ) : (
          <>
            {presets.length === 0 ? (
              <div className="muted small">Пока нет пресетов. Создай первый 👇</div>
            ) : (
              <ul className="preset-list">
                {presets.map((p) => (
                  <li key={p.id} className="preset-item">
                    <div className="preset-main">
                      <div className="preset-name">{p.name}</div>
                      <div className="preset-meta">
                        <span>{p.app_type}</span>
                        <span>{p.format}</span>
                      </div>
                    </div>
                    <div className="preset-actions">
                      <button
                        type="button"
                        className="button button-ghost"
                        onClick={() => handleOpenPreset(p)}
                        disabled={busyAction === `open-${p.id}`}
                      >
                        Открыть
                      </button>
                      <button
                        type="button"
                        className="button button-ghost danger"
                        onClick={() => handleDeletePreset(p.id)}
                        disabled={busyAction === `delete-${p.id}`}
                      >
                        ✕
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <PresetForm onCreate={handleCreatePreset} busy={busyAction === 'create-preset'} />
          </>
        )}
      </section>

      {presetPreview && (
        <section className="card">
          <div className="card-title">Конфиг пресета: {presetPreview.name}</div>
          <pre className="config-box">{presetPreview.config.value}</pre>
          <button
            type="button"
            className="button button-primary full-width"
            onClick={handleCopyConfig}
          >
            Скопировать в буфер
          </button>
        </section>
      )}
    </div>
  );
}

export default App;
