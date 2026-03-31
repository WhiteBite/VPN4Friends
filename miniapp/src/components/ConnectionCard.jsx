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
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontWeight: '600', fontSize: '15px', color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '16px', color: 'var(--primary)' }}>🔗</span> Ссылка подписки
            </div>
            <button 
              title="Показать QR-код для сканирования"
              onClick={() => setShowQr(!showQr)} 
              style={{ 
                background: showQr ? 'rgba(14, 165, 233, 0.15)' : 'rgba(255, 255, 255, 0.05)', 
                border: '1px solid',
                borderColor: showQr ? 'rgba(14, 165, 233, 0.3)' : 'rgba(255, 255, 255, 0.1)',
                color: showQr ? 'var(--primary)' : 'var(--text-hint)', 
                cursor: 'pointer',
                padding: '6px 12px',
                borderRadius: '8px',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                fontWeight: '600'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
              {showQr ? 'Скрыть QR' : 'QR-код'}
            </button>
          </div>
          
          {/* Animated QR Reveal */}
          <div style={{ 
            maxHeight: showQr ? '300px' : '0', 
            opacity: showQr ? 1 : 0, 
            overflow: 'hidden', 
            transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
            display: 'flex',
            justifyContent: 'center'
          }}>
            {subscriptionUrl && (
              <div style={{ margin: '8px 0 20px 0', background: '#fff', padding: '16px', borderRadius: '16px', width: 'max-content', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }}>
                <QRCodeSVG value={subscriptionUrl} size={160} level="M" includeMargin={false} />
              </div>
            )}
          </div>

          <div style={{ 
            display: 'flex', 
            alignItems: 'stretch', 
            background: 'rgba(0,0,0,0.4)', 
            borderRadius: '12px', 
            border: '1px solid rgba(255,255,255,0.08)',
            overflow: 'hidden'
          }}>
            <div style={{ 
              flex: 1, 
              whiteSpace: 'nowrap', 
              overflow: 'hidden', 
              textOverflow: 'ellipsis', 
              fontFamily: 'monospace', 
              fontSize: '13px',
              color: 'var(--text)',
              opacity: 0.8,
              padding: '14px 12px',
              display: 'flex',
              alignItems: 'center'
            }}>
              {subscriptionUrl || 'Формирование ссылки...'}
            </div>
            <button 
              onClick={onCopySubscription}
              style={{
                background: 'linear-gradient(135deg, var(--neon-blue), var(--btn))',
                color: '#fff',
                border: 'none',
                padding: '0 20px',
                fontWeight: '600',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                transition: 'filter 0.2s',
              }}
              onMouseOver={e => e.currentTarget.style.filter = 'brightness(1.1)'}
              onMouseOut={e => e.currentTarget.style.filter = 'brightness(1)'}
            >
              <IconCopy /> Копировать
            </button>
          </div>
        </div>

        {/* Compact Apps Guide */}
        <div>
          <div style={{ fontSize: '11px', fontWeight: '800', color: 'var(--text-hint)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: '12px', textAlign: 'center' }}>
            Приложения для подключения
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '12px' }}>
            <div style={{ 
              background: 'rgba(255,255,255,0.02)', 
              borderRadius: '16px', 
              padding: '12px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              border: '1px solid rgba(255,255,255,0.06)',
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)'
            }}>
              <img src="https://v2rayng.org/assets/images/logo.png" style={{ width: '40px', height: '40px', borderRadius: '10px', objectFit: 'cover' }} alt="v2rayNG" />
              <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>v2rayNG</div>
                <div style={{ fontSize: '12px', color: 'var(--text-hint)', fontWeight: '500' }}>Android</div>
              </div>
            </div>
            
            <div style={{ 
              background: 'rgba(255,255,255,0.02)', 
              borderRadius: '16px', 
              padding: '12px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              border: '1px solid rgba(255,255,255,0.06)',
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)'
            }}>
              <div style={{ width: '40px', height: '40px', background: 'linear-gradient(135deg, #0EA5E9, #2563EB)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '20px', fontWeight: 'bold', boxShadow: '0 4px 12px var(--neon-blue-glow)' }}>S</div>
              <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Streisand</div>
                <div style={{ fontSize: '12px', color: 'var(--text-hint)', fontWeight: '500' }}>iOS / Apple</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
