import React from 'react';
import { QRCodeSVG } from 'qrcode.react';

import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { IconLock, IconCopy, IconCheckCircle, IconGlobe } from '../ui/Icons';

export default function ConnectionCard({ profile, endpoint, onCopy, link, onRequest, isBusy }) {
  const hasProfile = profile?.has_profile;

  if (!hasProfile) {
    const status = profile?.request_status;

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
              <div className="empty-text">
                К сожалению, модератор отклонил ваш запрос на доступ.
              </div>
            </>
          ) : (
            <>
              <div className="empty-icon"><IconLock /></div>
              <div className="empty-title">Нет VPN</div>
              <div className="empty-text" style={{ marginBottom: '24px' }}>
                Чтобы получить свой личный VPN и начать пользоваться сервисом, отправь заявку.
              </div>
              <Button 
                variant="primary" 
                style={{ width: '100%', padding: '16px', borderRadius: 'var(--r-pill)', fontSize: '16px', fontWeight: '600' }}
                onClick={onRequest}
                isLoading={isBusy}
              >
                Запросить доступ
              </Button>
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
