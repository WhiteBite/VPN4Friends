import React, { useEffect, useState, useCallback } from 'react';
import { fetchAdminRequests, approveRequest, rejectRequest, sendAdminBroadcast, fetchUsers, revokeUserVpn } from '../api';
import Card from '../ui/Card';
import Button from '../ui/Button';
import AdminChats from './AdminChats';
import { IconMessage } from '../ui/Icons';
import { getTelegram } from '../telegram';

const MOCK_REQUESTS = [
  { id: 1, full_name: 'Вася Пупкин', telegram_id: 12345678, status: 'pending', created_at: new Date().toISOString() },
  { id: 2, full_name: 'Оля', username: 'olya', telegram_id: 87654321, status: 'pending', created_at: new Date(Date.now() - 3600000).toISOString() },
];

const formatBytes = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

export default function AdminPanel({ onError, onSuccess }) {
  const [activeTab, setActiveTab] = useState('requests'); // 'requests', 'broadcast', 'chats', 'users', 'servers'
  
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(null);
  const [rejectConfirmId, setRejectConfirmId] = useState(null);
  const [endpoints, setEndpoints] = useState([]);
  const [syncingAll, setSyncingAll] = useState(false);

  // Broadcast state
  const [broadcastText, setBroadcastText] = useState('');
  const [broadcastTarget, setBroadcastTarget] = useState('all');
  const [sendingBroadcast, setSendingBroadcast] = useState(false);

  // Users tab state
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [revokeConfirmId, setRevokeConfirmId] = useState(null);
  const [revoking, setRevoking] = useState(null);

  const isDev = import.meta.env.DEV;

  const handleBroadcast = async () => {
    if (!broadcastText.trim()) {
      onError('Введите текст сообщения');
      return;
    }
    setSendingBroadcast(true);
    try {
      if (!isDev) {
        await sendAdminBroadcast({ message: broadcastText, target: broadcastTarget });
      }
      onSuccess('Рассылка поставлена в очередь!');
      setBroadcastText(''); // clear on success
    } catch (err) {
      onError(err.message || 'Ошибка запуска рассылки');
    } finally {
      setSendingBroadcast(false);
    }
  };

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      if (isDev) {
        setRequests(MOCK_REQUESTS);
      } else {
        const data = await fetchAdminRequests();
        setRequests(data || []);
      }
    } catch (err) {
      if (!isDev) onError(err.message || 'Ошибка загрузки заявок');
    } finally {
      setLoading(false);
    }
  }, [isDev, onError]);

  const fetchData = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      if (activeTab === 'requests') {
        const data = await fetchAdminRequests();
        setRequests(data || []);
      } else if (activeTab === 'users') {
        const data = await fetchUsers();
        setUsers(data || []);
      }
    } catch (e) {
      onError(e.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, [activeTab, loading, onError]);

  const loadUsers = useCallback(async () => {
    try {
      setUsersLoading(true);
      const data = await fetchUsers();
      setUsers(data || []);
    } catch (err) {
      if (!isDev) onError(err.message || 'Ошибка загрузки пользователей');
    } finally {
      setUsersLoading(false);
    }
  }, [isDev, onError]);

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      onSuccess('Синхронизация запущена (TODO)');
    } catch (err) {
      onError('Ошибка синхронизации');
    } finally {
      setSyncingAll(false);
    }
  };

  useEffect(() => {
    loadRequests();
    
    // Listen for WebSocket NEW_REQUEST triggers from App.jsx
    const handleRefresh = () => {
      loadRequests();
    };
    
    window.addEventListener('refresh_admin_data', handleRefresh);
    return () => {
      window.removeEventListener('refresh_admin_data', handleRefresh);
    };
  }, [loadRequests]);

  const handleApprove = async (id) => {
    setProcessing(id);
    setRejectConfirmId(null);
    try {
      if (!isDev) {
        await approveRequest(id);
      }
      setRequests((prev) => prev.filter((r) => r.id !== id));
      onSuccess('Заявка одобрена');
    } catch (err) {
      onError(err.message || 'Ошибка одобрения');
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (id) => {
    if (rejectConfirmId !== id) {
      setRejectConfirmId(id);
      return;
    }
    
    setProcessing(id);
    try {
      if (!isDev) {
        await rejectRequest(id);
      }
      setRequests((prev) => prev.filter((r) => r.id !== id));
      onSuccess('Заявка отклонена');
      setRejectConfirmId(null);
    } catch (err) {
      onError(err.message || 'Ошибка отклонения');
    } finally {
      setProcessing(null);
    }
  };

  const handleRevoke = async (userId) => {
    if (revokeConfirmId !== userId) {
      setRevokeConfirmId(userId);
      return;
    }
    setRevoking(userId);
    try {
      const res = await revokeUserVpn(userId);
      onSuccess(res.message || 'VPN удалён');
      setRevokeConfirmId(null);
      loadUsers(); // refresh
    } catch (err) {
      onError(err.message || 'Ошибка удаления VPN');
    } finally {
      setRevoking(null);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
  }, [activeTab, loadUsers]);

  if (loading) {
    return <div className="empty-state">Загрузка панели...</div>;
  }

  const renderRequests = () => {
    if (requests.length === 0) {
      return (
        <div className="empty-state">
          <div className="empty-icon">✅</div>
          <div className="empty-title">Всё чисто</div>
          <div className="empty-text">Новых заявок на VPN нет.</div>
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h3 style={{ marginBottom: '8px', fontSize: '18px', fontWeight: 'bold' }}>Новые заявки ({requests.length})</h3>
        {requests.map((req) => (
          <div 
            key={req.id} 
            style={{ 
              padding: '16px', 
              background: 'var(--bg-elevated)', 
              borderRadius: '12px',
              border: '1px solid var(--border)' 
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <div style={{ fontWeight: '600', fontSize: '16px', color: 'var(--text)' }}>
                  {req.full_name}
                </div>
                {req.username && (
                  <div 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '4px', 
                      marginTop: '4px',
                      color: 'var(--accent)',
                      fontSize: '14px',
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      const tg = getTelegram();
                      if (tg) {
                        tg.openTelegramLink(`https://t.me/${req.username}`);
                      } else {
                        window.open(`https://t.me/${req.username}`, '_blank');
                      }
                    }}
                  >
                    <IconMessage size={14} />
                    <span>@{req.username}</span>
                  </div>
                )}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                #{req.id}
              </div>
            </div>
            
            {req.user_comment && (
              <div style={{ 
                padding: '8px 12px', 
                marginBottom: '12px',
                background: 'var(--bg)', 
                borderRadius: '8px', 
                fontSize: '13px', 
                color: 'var(--text-muted)',
                borderLeft: '3px solid var(--accent)'
              }}>
                💬 {req.user_comment}
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px' }}>
              <Button 
                variant="primary" 
                style={{ flex: 1, padding: '10px', fontSize: '14px', borderRadius: '8px' }}
                onClick={() => handleApprove(req.id)}
                isLoading={processing === req.id}
              >
                Одобрить
              </Button>
              <Button 
                variant={rejectConfirmId === req.id ? "danger" : "secondary"} 
                style={{ 
                  flex: 1, 
                  padding: '10px', 
                  fontSize: '14px', 
                  borderRadius: '8px', 
                  background: rejectConfirmId === req.id ? 'var(--error, #ff4d4f)' : 'var(--surface)',
                  color: rejectConfirmId === req.id ? '#fff' : 'inherit'
                }}
                onClick={() => handleReject(req.id)}
                disabled={processing === req.id}
              >
                {rejectConfirmId === req.id ? 'Точно?' : 'Отклонить'}
              </Button>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderBroadcast = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px' }}>Новая рассылка</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            Сообщение будет отправлено от лица бота. Поддерживается HTML-разметка.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Получатели</label>
          <select 
            value={broadcastTarget}
            onChange={(e) => setBroadcastTarget(e.target.value)}
            style={{ 
              padding: '12px', 
              borderRadius: '12px', 
              background: 'var(--bg-elevated)', 
              border: '1px solid var(--border)',
              color: 'var(--text)',
              fontSize: '15px',
              outline: 'none'
            }}
          >
            <option value="all" style={{ background: '#1c1c1e', color: '#fff' }}>Всем пользователям бота</option>
            <option value="with_vpn" style={{ background: '#1c1c1e', color: '#fff' }}>Только тем, у кого есть VPN</option>
            <option value="without_vpn" style={{ background: '#1c1c1e', color: '#fff' }}>Тем, у кого отключен VPN</option>
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Сообщение</label>
          <textarea
            value={broadcastText}
            onChange={(e) => setBroadcastText(e.target.value)}
            placeholder="Введите текст рассылки..."
            rows={5}
            style={{ 
              width: '100%', 
              padding: '12px', 
              borderRadius: '12px', 
              background: 'var(--bg-elevated)', 
              border: '1px solid var(--border)',
              color: 'var(--text)',
              fontSize: '15px',
              resize: 'none',
              outline: 'none'
            }}
          />
        </div>

        <Button 
          variant="primary" 
          onClick={handleBroadcast} 
          isLoading={sendingBroadcast}
          style={{ padding: '14px', fontSize: '16px', fontWeight: 'bold', borderRadius: '12px', marginTop: '8px' }}
        >
          Запустить рассылку
        </Button>
        <div style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)', marginTop: '-4px' }}>
          ℹ️ Если нужно отправить картинку или видео, используйте команду /broadcast прямо в телеграм боте.
        </div>
      </div>
    );
  };

  const renderUsers = () => {
    if (usersLoading) return <div className="empty-state">Загрузка...</div>;

    const vpnUsers = users.filter(u => u.has_vpn);
    const noVpnUsers = users.filter(u => !u.has_vpn);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
          Всего: {users.length} | С VPN: {vpnUsers.length} | Без VPN: {noVpnUsers.length}
        </div>

        {vpnUsers.length > 0 && (
          <>
            <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>🟢 С активным VPN</h3>
            {vpnUsers.map(u => (
              <div key={u.id} style={{
                padding: '12px 16px',
                background: 'var(--bg-elevated)',
                borderRadius: '12px',
                border: '1px solid var(--border)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{u.full_name}</div>
                  <div style={{ fontSize: 13, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    {u.username && <span>@{u.username}</span>}
                    {u.stats && (
                      <span style={{ fontSize: '11px', color: 'var(--text-hint)', background: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                        <span data-tooltip="Отдано" style={{ color: 'var(--success)', cursor: 'help' }}>↑</span> {formatBytes(u.stats.upload)} <span style={{opacity: 0.5}}>|</span> <span data-tooltip="Скачано" style={{ color: '#3b82f6', cursor: 'help' }}>↓</span> {formatBytes(u.stats.download)}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                    <span>{u.protocol}</span>
                    <span style={{opacity: 0.5}}>·</span>
                    {u.client_id ? (
                      <span style={{ fontFamily: 'monospace' }}>🆔 {u.client_id.slice(0, 8)}...</span>
                    ) : (
                      <span data-tooltip="Старый формат профиля без Client ID" style={{ padding: '2px 6px', background: 'rgba(239, 68, 68, 0.2)', color: '#EF4444', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', cursor: 'help' }}>
                        ⚠️ Устаревший
                      </span>
                    )}
                  </div>
                  {u.client_id && (
                    <div style={{ fontSize: 11, color: 'var(--success, #52c41a)', marginTop: 4, fontWeight: 500 }}>
                      ✓ Unified Access
                    </div>
                  )}
                </div>
                <button
                  data-tooltip="Отозвать VPN"
                  onClick={() => handleRevoke(u.id)}
                  disabled={revoking === u.id}
                  style={{
                    padding: '8px',
                    borderRadius: '8px',
                    border: '1px solid ' + (revokeConfirmId === u.id ? '#ff4d4f' : 'rgba(255,255,255,0.1)'),
                    fontSize: '16px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    background: revokeConfirmId === u.id ? '#ff4d4f' : 'rgba(239, 68, 68, 0.1)',
                    color: revokeConfirmId === u.id ? '#fff' : '#EF4444',
                    opacity: revoking === u.id ? 0.5 : 1,
                  }}
                >
                  {revoking === u.id ? '⌛' : revokeConfirmId === u.id ? 'Точно?' : '🗑️'}
                </button>
              </div>
            ))}
          </>
        )}

        {noVpnUsers.length > 0 && (
          <>
            <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginTop: '8px' }}>⚪ Без VPN</h3>
            {noVpnUsers.map(u => (
              <div key={u.id} style={{
                padding: '12px 16px',
                background: 'var(--bg-elevated)',
                borderRadius: '12px',
                border: '1px solid var(--border)',
                opacity: 0.7
              }}>
                <div style={{ fontWeight: 600, fontSize: '15px' }}>{u.full_name}</div>
                {u.username && <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>@{u.username}</div>}
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  const renderServers = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <Button variant="primary" onClick={handleSyncAll} isLoading={syncingAll}>
        Синхронизировать всех
      </Button>
      <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
        Серверы активны и работают в штатном режиме.
      </div>
    </div>
  );

  return (
    <div style={{ paddingBottom: '30px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <button 
          onClick={() => setActiveTab('requests')}
          style={{ 
            flex: 1, 
            padding: '12px', 
            borderRadius: '12px', 
            border: 'none', 
            background: activeTab === 'requests' ? 'var(--accent)' : 'var(--bg-elevated)', 
            color: activeTab === 'requests' ? '#000' : 'var(--text)', 
            fontWeight: '600',
            fontSize: '14px',
            transition: 'all 0.2s',
            cursor: 'pointer'
          }}>
          Заявки {requests.length > 0 && `(${requests.length})`}
        </button>
        <button 
          onClick={() => setActiveTab('broadcast')}
          style={{ 
            flex: 1, 
            padding: '12px', 
            borderRadius: '12px', 
            border: 'none', 
            background: activeTab === 'broadcast' ? 'var(--accent)' : 'var(--bg-elevated)', 
            color: activeTab === 'broadcast' ? '#000' : 'var(--text)', 
            fontWeight: '600',
            fontSize: '14px',
            transition: 'all 0.2s',
            cursor: 'pointer'
          }}>
          Рассылка
        </button>
        <button 
          onClick={() => setActiveTab('chats')}
          style={{ 
            flex: 1, 
            padding: '12px', 
            borderRadius: '12px', 
            border: 'none', 
            background: activeTab === 'chats' ? 'var(--accent)' : 'var(--bg-elevated)', 
            color: activeTab === 'chats' ? '#000' : 'var(--text)', 
            fontWeight: '600',
            fontSize: '14px',
            transition: 'all 0.2s',
            cursor: 'pointer'
          }}>
          Чаты
        </button>
        <button 
          onClick={() => setActiveTab('users')}
          style={{ 
            flex: 1, 
            padding: '12px', 
            borderRadius: '12px', 
            border: 'none', 
            background: activeTab === 'users' ? 'var(--accent)' : 'var(--bg-elevated)', 
            color: activeTab === 'users' ? '#000' : 'var(--text)', 
            fontWeight: '600',
            fontSize: '14px',
            transition: 'all 0.2s',
            cursor: 'pointer'
          }}>
          Юзеры
        </button>
        <button 
          onClick={() => setActiveTab('servers')}
          style={{ 
            flex: 1, 
            padding: '12px', 
            borderRadius: '12px', 
            border: 'none', 
            background: activeTab === 'servers' ? 'var(--accent)' : 'var(--bg-elevated)', 
            color: activeTab === 'servers' ? '#000' : 'var(--text)', 
            fontWeight: '600',
            fontSize: '14px',
            transition: 'all 0.2s',
            cursor: 'pointer'
          }}>
          Серверы
        </button>
      </div>

      {activeTab === 'chats' ? (
        <AdminChats onError={onError} onSuccess={onSuccess} />
      ) : (
        <Card style={{ padding: '20px' }}>
          {activeTab === 'requests' ? renderRequests() : activeTab === 'users' ? renderUsers() : activeTab === 'servers' ? renderServers() : renderBroadcast()}
        </Card>
      )}
    </div>
  );
}
