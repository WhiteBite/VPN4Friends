import { useState, useCallback, useEffect } from 'react';
import {
  fetchMe,
  fetchProtocols,
  fetchLink,
  fetchEndpoints,
  selectEndpoint,
  switchProtocol,
  updateSni,
  requestVpn,
  revokeMe
} from '../api';
import { MOCK_DATA } from '../mockData';

const isDev = import.meta.env.DEV;

async function safeFetch(fetcher, fallback) {
  try {
    return await fetcher();
  } catch (err) {
    if (isDev && fallback !== undefined) return fallback;
    throw new Error(err?.message || 'API unavailable');
  }
}

export function useVPN(showToast) {
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState(null);
  const [protocols, setProtocols] = useState([]);
  const [endpoints, setEndpoints] = useState([]);
  const [currentEndpoint, setCurrentEndpoint] = useState(null);
  const [vpnLink, setVpnLink] = useState(null);
  const [busy, setBusy] = useState('');

  const refreshLink = async () => {
    try {
      const linkData = await safeFetch(fetchLink, { link: MOCK_DATA.link });
      setVpnLink(linkData.link);
    } catch {
      // noop
    }
  };

  const refreshMe = async () => {
    try {
      const data = await safeFetch(fetchMe, MOCK_DATA.me);
      setMe(data);
    } catch {
      showToast('Ошибка обновления данных.', 'error');
    }
  };

  const loadAll = async () => {
    try {
      const meData = await safeFetch(fetchMe, MOCK_DATA.me);
      setMe(meData);
      setLoading(false);

      Promise.all([
        safeFetch(fetchProtocols, MOCK_DATA.protocols),
        safeFetch(fetchEndpoints, MOCK_DATA.endpoints),
      ]).then(([protocolData, endpointData]) => {
        setProtocols(protocolData);
        setEndpoints(endpointData);
        if (endpointData.length > 0) setCurrentEndpoint(endpointData[0].name);
      });

      if (meData?.profile?.has_profile) {
        try {
          const linkData = await safeFetch(fetchLink, { link: MOCK_DATA.link });
          setVpnLink(linkData.link);
        } catch {
          // noop
        }
      }
    } catch {
      showToast('Не удалось загрузить данные.', 'error');
      setLoading(false);
    }
  };

  const handleSelectEndpoint = async (name, andCopy = false) => {
    setBusy('endpoint');
    try {
      if (name !== currentEndpoint) {
        await safeFetch(() => selectEndpoint(name), { success: true });
        setCurrentEndpoint(name);
        const linkData = await safeFetch(fetchLink, { link: MOCK_DATA.link });
        setVpnLink(linkData.link);
        showToast('Точка входа изменена.', 'success');
        
        if (andCopy) {
           await navigator.clipboard.writeText(linkData.link);
           setTimeout(() => showToast('Ссылка скопирована!', 'success'), 300);
        }
      } else if (andCopy) {
         if (vpnLink) {
           await navigator.clipboard.writeText(vpnLink);
           showToast('Ссылка скопирована!', 'success');
         }
      }
    } catch {
      showToast('Ошибка смены точки входа.', 'error');
    } finally {
      setBusy('');
    }
  };

  const handleSwitchProtocol = async (protocol) => {
    setBusy('protocol');
    try {
      await safeFetch(() => switchProtocol(protocol), { success: true });
      await refreshMe();
      await refreshLink();
      showToast('Протокол переключён.', 'success');
    } catch {
      showToast('Не удалось переключить протокол.', 'error');
    } finally {
      setBusy('');
    }
  };

  const handleUpdateSni = async (sni) => {
    setBusy('sni');
    try {
      await safeFetch(() => updateSni(sni), { success: true });
      await refreshMe();
      await refreshLink();
      showToast('SNI обновлён.', 'success');
    } catch {
      showToast('Не удалось обновить SNI.', 'error');
    } finally {
      setBusy('');
    }
  };

  const handleRequestVpn = async (comment = '') => {
    setBusy('request');
    try {
      const resp = await safeFetch(() => requestVpn(comment), { success: true, message: 'Mock Заявка отправлена' });
      showToast(resp.message || 'Заявка отправлена!', 'success');
      await refreshMe();
    } catch (err) {
      showToast(err.message || 'Ошибка отправки заявки.', 'error');
    } finally {
      setBusy('');
    }
  };

  const handleRevokeVpn = async () => {
    setBusy('revoke');
    try {
      const resp = await safeFetch(() => revokeMe(), { success: true, message: 'VPN отозван' });
      showToast(resp.message || 'VPN отозван!', 'success');
      await loadAll();
    } catch (err) {
      showToast(err.message || 'Ошибка удаления VPN.', 'error');
    } finally {
      setBusy('');
    }
  };

  return {
    loading,
    me,
    protocols,
    endpoints,
    currentEndpoint,
    vpnLink,
    busy,
    loadAll,
    refreshMe,
    handleSelectEndpoint,
    handleSwitchProtocol,
    handleUpdateSni,
    handleRequestVpn,
    handleRevokeVpn
  };
}
