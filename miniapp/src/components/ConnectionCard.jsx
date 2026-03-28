import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';

import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { IconLock, IconCopy, IconCheckCircle, IconGlobe } from '../ui/Icons';

export default function ConnectionCard({ profile, endpoint, onCopy, link, onRequest, isBusy }) {
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
          <IconCheckCircle /> Готов к работе
        </Badge>
      </div>

      {/* Location Display */}
      <div className="hero-location">
        <div className="location-icon">
          <IconGlobe size={24} color="currentColor" />
        </div>
        <div className="location-info">
          <div className="location-label">Текущая локация</div>
          <div className="location-name">{endpoint?.label || 'Загрузка...'}</div>
        </div>
      </div>

      {/* Action Area */}
      {link ? (
        <div className="hero-action-area">
          <Button variant="custom" className="btn-copy-main" onClick={onCopy}>
            <span className="btn-icon"><IconCopy /></span>
            Скопировать ссылку
          </Button>
          
          <div className="qr-toggle-container">
            <Button 
              variant="custom"
              className="btn-text-muted" 
              onClick={() => document.getElementById('qr-wrapper').classList.toggle('qr-wrapper--open')}
            >
              Показать QR-код
            </Button>
            <div id="qr-wrapper" className="qr-wrapper">
              <div className="qr-box">
                <QRCodeSVG
                  value={link}
                  size={160}
                  bgColor="transparent"
                  fgColor="#090B0F"
                  level="M"
                  includeMargin={false}
                />
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="hero-action-area">
          <div className="skeleton skeleton--box" style={{ height: 56, borderRadius: '14px', width: '100%', marginBottom: '16px' }}></div>
        </div>
      )}
    </Card>
  );
}
