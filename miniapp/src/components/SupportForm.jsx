import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { sendSupportMessage } from '../api';

export default function SupportForm({ onError, onSuccess }) {
  const [isOpen, setIsOpen] = useState(false);
  const [text, setText] = useState('');
  const [isSending, setIsSending] = useState(false);

  const handleSend = async () => {
    if (!text.trim()) {
      onError('Пожалуйста, введите текст сообщения');
      return;
    }

    setIsSending(true);
    try {
      await sendSupportMessage(text);
      onSuccess('Сообщение успешно отправлено!');
      setText('');
      setIsOpen(false);
    } catch (err) {
      onError(err.message || 'Ошибка отправки сообщения');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Card style={{ marginTop: '16px' }}>
      <div className="card-title">💬 Поддержка</div>
      
      {!isOpen ? (
        <Button
          variant="secondary"
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', fontSize: '15px' }}
          onClick={() => setIsOpen(true)}
        >
          Написать администратору
        </Button>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Опишите вашу проблему..."
            rows={4}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--bg-elevated)',
              color: 'var(--text)',
              fontSize: '14px',
              resize: 'none',
              fontFamily: 'inherit'
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="secondary"
              style={{ flex: 1 }}
              onClick={() => {
                setIsOpen(false);
                setText('');
              }}
              disabled={isSending}
            >
              Отмена
            </Button>
            <Button
              variant="primary"
              style={{ flex: 1 }}
              onClick={handleSend}
              isLoading={isSending}
            >
              Отправить
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
