import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';

import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { IconCheckCircle, IconCopy } from '../ui/Icons';

export default function ConnectionCard({ profile, subscriptionUrl, onCopySubscription, onRequest, isBusy }) {
  const hasProfile = profile?.has_profile;
  const [comment, setComment] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [showQr, setShowQr] = useState(false);

  const handleSubmitRequest = () => {
    onRequest(comment);
  };

  if (!hasProfile) {
    const status = profile?.request_status;

    // Common request form
    const renderRequestForm = () => {
      if (!showForm) {
        return (
          <Button 
            variant="primary" 
            style={{ width: '100%', padding: '16px', borderRadius: 'var(--r-pill)', fontSize: '16px', fontWeight: '600' }}
            onClick={() => setShowForm(true)}
            isLoading={isBusy}
          >
            {status === 'rejected' ? 'Запросить повторно' : 'Запросить доступ'}
          </Button>
        );
      }

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Напишите, зачем вам VPN (необязательно)..."
            rows={3}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '12px',
              border: '1px solid var(--border)',
              background: 'var(--bg-elevated)',
              color: 'var(--text)',
              fontSize: '14px',
              resize: 'none',
              fontFamily: 'inherit',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="secondary"
              style={{ flex: 1, padding: '14px', borderRadius: 'var(--r-pill)', fontSize: '15px' }}
              onClick={() => { setShowForm(false); setComment(''); }}
              disabled={isBusy}
            >
              Назад
            </Button>
            <Button
              variant="primary"
              style={{ flex: 1, padding: '14px', borderRadius: 'var(--r-pill)', fontSize: '15px', fontWeight: '600' }}
              onClick={handleSubmitRequest}
              isLoading={isBusy}
            >
              Отправить
            </Button>
          </div>
        </div>
      );
    };

    return (
      <Card hero>
        <div className="empty-state">
          {status === 'pending' ? (
            <>
              <div className="empty-icon">⏳</div>
              <div className="empty-title">Заявка на рассмотрении</div>
              <div className="empty-text">
                Ожидайте одобрения модератором.
              </div>
            </>
          ) : status === 'rejected' ? (
            <>
              <div className="empty-icon">❌</div>
              <div className="empty-title">Заявка отклонена</div>
              <div className="empty-text" style={{ marginBottom: '16px' }}>
                Модератор почти сразу отклонил ваш запрос (или он просрочен). Вы можете попробовать еще раз!
              </div>
              {renderRequestForm()}
            </>
          ) : (
            <>
              <div className="empty-icon">🔒</div>
              <div className="empty-title">Нет VPN</div>
              <div className="empty-text" style={{ marginBottom: '24px' }}>
                Чтобы получить свой личный VPN и начать пользоваться сервисом, отправь заявку.
              </div>
              {renderRequestForm()}
            </>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card hero style={{ padding: '24px 16px', position: 'relative', overflow: 'hidden' }}>
      {/* Decorative background glow */}
      <div style={{ position: 'absolute', top: '-50px', left: '-50px', width: '150px', height: '150px', background: 'var(--primary)', filter: 'blur(80px)', opacity: 0.15, borderRadius: '50%' }} />
      <div style={{ position: 'absolute', bottom: '-50px', right: '-50px', width: '150px', height: '150px', background: 'var(--success)', filter: 'blur(80px)', opacity: 0.1, borderRadius: '50%' }} />

      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
          <Badge type="success" style={{ fontSize: '13px', padding: '6px 16px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
            <IconCheckCircle /> Подписка активна
          </Badge>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '26px', fontWeight: '800', margin: '0 0 8px', letterSpacing: '-0.5px' }}>Ваш VPN Готов 🚀</h2>
          <p style={{ color: 'var(--text-hint)', fontSize: '14px', margin: 0, lineHeight: '1.4' }}>
            Скопируйте ссылку ниже и добавьте её в приложение.
          </p>
        </div>

        <div style={{ 
          background: 'var(--bg-elevated)', 
          borderRadius: '16px', 
          padding: '16px', 
          marginBottom: '24px', 
          border: '1px solid var(--border)',
          boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text)' }}>Ссылка подписки</div>
            <button 
              onClick={() => setShowQr(!showQr)} 
              style={{ 
                background: 'transparent', 
                border: 'none', 
                color: 'var(--primary)', 
                fontSize: '13px', 
                fontWeight: '600', 
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: '6px',
                transition: 'background 0.2s'
              }}
              onMouseOver={e => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)'}
              onMouseOut={e => e.currentTarget.style.background = 'transparent'}
            >
              {showQr ? 'Скрыть QR' : 'Показать QR'}
            </button>
          </div>
          
          {showQr && subscriptionUrl && (
            <div style={{ display: 'flex', justifyContent: 'center', margin: '0 0 16px 0', background: '#fff', padding: '16px', borderRadius: '12px', width: 'max-content', alignSelf: 'center', marginInline: 'auto', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
              <QRCodeSVG value={subscriptionUrl} size={160} level="M" includeMargin={false} />
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ 
              flex: 1, 
              whiteSpace: 'nowrap', 
              overflow: 'hidden', 
              textOverflow: 'ellipsis', 
              fontFamily: 'monospace', 
              fontSize: '13px',
              color: 'var(--text)',
              opacity: 0.9
            }}>
              {subscriptionUrl || 'Загрузка...'}
            </div>
            <Button variant="primary" style={{ padding: '10px 16px', borderRadius: '10px', fontSize: '14px', fontWeight: '600', whiteSpace: 'nowrap', boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)' }} onClick={onCopySubscription}>
              <IconCopy /> Копировать
            </Button>
          </div>
        </div>

        {/* Compact Apps Guide */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-hint)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px', textAlign: 'center' }}>
            Приложения для подключения
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '12px' }}>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: '14px', padding: '12px', display: 'flex', alignItems: 'center', gap: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <img src="https://v2rayng.org/assets/images/logo.png" style={{ width: '36px', height: '36px', borderRadius: '8px', objectFit: 'cover' }} alt="v2rayNG" />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>v2rayNG</div>
                <div style={{ fontSize: '12px', color: 'var(--text-hint)' }}>Android</div>
              </div>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: '14px', padding: '12px', display: 'flex', alignItems: 'center', gap: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, #3b82f6, #2563eb)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '20px', fontWeight: 'bold', boxShadow: '0 2px 6px rgba(59, 130, 246, 0.4)' }}>S</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Streisand</div>
                <div style={{ fontSize: '12px', color: 'var(--text-hint)' }}>iOS / Apple</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
