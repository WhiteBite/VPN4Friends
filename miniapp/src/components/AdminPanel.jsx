import React, { useEffect, useState, useCallback } from 'react';
import { fetchAdminRequests, approveRequest, rejectRequest, sendAdminBroadcast } from '../api';
import Card from '../ui/Card';
import Button from '../ui/Button';
import AdminChats from './AdminChats';
import { IconMessage } from '../ui/Icons';
import { getTelegram } from '../telegram';

const MOCK_REQUESTS = [
  { id: 1, full_name: 'Вася Пупкин', telegram_id: 12345678, status: 'pending', created_at: new Date().toISOString() },
  { id: 2, full_name: 'Оля', username: 'olya', telegram_id: 87654321, status: 'pending', created_at: new Date(Date.now() - 3600000).toISOString() },
];

export default function AdminPanel({ onError, onSuccess }) {
  const [activeTab, setActiveTab] = useState('requests'); // 'requests', 'broadcast', 'chats'
  
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(null);

  // Broadcast state
  const [broadcastText, setBroadcastText] = useState('');
  const [broadcastTarget, setBroadcastTarget] = useState('all');
  const [sendingBroadcast, setSendingBroadcast] = useState(false);

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
      const data = await fetchAdminRequests();
      setRequests(data || []);
    } catch (err) {
      if (isDev) {
        // Use mock data in development
        setRequests(MOCK_REQUESTS);
      } else {
        onError(err.message || 'Ошибка загрузки заявок');
      }
    } finally {
      setLoading(false);
    }
  }, [isDev, onError]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const handleApprove = async (id) => {
    setProcessing(id);
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
    if (!window.confirm('Точно отклонить заявку?')) return;
    setProcessing(id);
    try {
      if (!isDev) {
        await rejectRequest(id);
      }
      setRequests((prev) => prev.filter((r) => r.id !== id));
      onSuccess('Заявка отклонена');
    } catch (err) {
      onError(err.message || 'Ошибка отклонения');
    } finally {
      setProcessing(null);
    }
  };

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
                variant="secondary" 
                style={{ flex: 1, padding: '10px', fontSize: '14px', borderRadius: '8px', background: 'var(--surface)' }}
                onClick={() => handleReject(req.id)}
                disabled={processing === req.id}
              >
                Отклонить
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

  return (
    <div style={{ paddingBottom: '30px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', gap: '8px' }}>
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
            fontSize: '15px',
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
            fontSize: '15px',
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
            fontSize: '15px',
            transition: 'all 0.2s',
            cursor: 'pointer'
          }}>
          Поддержка
        </button>
      </div>

      {activeTab === 'chats' ? (
        <AdminChats onError={onError} onSuccess={onSuccess} />
      ) : (
        <Card style={{ padding: '20px' }}>
          {activeTab === 'requests' ? renderRequests() : renderBroadcast()}
        </Card>
      )}
    </div>
  );
}
