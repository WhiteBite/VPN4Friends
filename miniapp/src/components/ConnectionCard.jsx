import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';

import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { IconLock, IconCopy, IconCheckCircle, IconGlobe } from '../ui/Icons';

export default function ConnectionCard({ profile, onCopySubscription, onRequest, isBusy }) {
  const hasProfile = profile?.has_profile;
  const [comment, setComment] = useState('');
  const [showForm, setShowForm] = useState(false);

  const handleSubmitRequest = () => {
    onRequest(comment);
  };

  if (!hasProfile) {
    const status = profile?.request_status;

    // Common request form (used in both "no status" and "rejected" states)
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
                Ожидайте одобрения модератором. Обычно это занимает пару минут.
              </div>
            </>
          ) : status === 'rejected' ? (
            <>
              <div className="empty-icon">❌</div>
              <div className="empty-title">Заявка отклонена</div>
              <div className="empty-text" style={{ marginBottom: '16px' }}>
                К сожалению, модератор отклонил ваш запрос. Вы можете отправить заявку повторно.
              </div>
              {renderRequestForm()}
            </>
          ) : (
            <>
              <div className="empty-icon"><IconLock /></div>
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
    <Card hero>
      <div className="hero-status">
        <Badge type="success">
          <IconCheckCircle /> Подписка активна
        </Badge>
      </div>

      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div style={{ fontSize: '64px', marginBottom: '16px', animation: 'float 4s ease-in-out infinite' }}>📡</div>
        <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>Твоя Авто-Подписка</h2>
        <p style={{ color: 'var(--text-hint)', fontSize: '14px', lineHeight: '1.5', maxWidth: '280px', margin: '0 auto' }}>
          Добавь эту ссылку в приложение (Throne / v2rayNG), и все сервера загрузятся автоматически.
        </p>
      </div>

      <div className="hero-action-area">
        <Button variant="custom" className="btn-copy-main" onClick={onCopySubscription} style={{ width: '100%', padding: '18px 24px', fontSize: '18px' }}>
          <span className="btn-icon"><IconCopy /></span>
          Скопировать ссылку
        </Button>
      </div>
      
      <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <p style={{ fontSize: '12px', color: 'var(--text-hint)', textAlign: 'center' }}>
          Нужен один конкретный сервер или QR-код? Перейди во вкладку <strong>Локации</strong>.
        </p>
      </div>
    </Card>
  );
}
