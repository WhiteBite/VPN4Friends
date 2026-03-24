import React from 'react';
import { QRCodeSVG } from 'qrcode.react';

export default function QRModal({ link, visible, onClose }) {
  if (!visible || !link) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <span className="modal__title">QR-код для подключения</span>
          <button type="button" className="modal__close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal__body">
          <div className="qr-container">
            <QRCodeSVG
              value={link}
              size={240}
              bgColor="transparent"
              fgColor="#f1f5f9"
              level="M"
              includeMargin={false}
            />
          </div>
          <div className="qr-hint">
            Отсканируй камерой или импортируй в VPN-приложение
          </div>
        </div>
      </div>
    </div>
  );
}
