import React, { useEffect } from 'react';

export default function Toast({ message, type = 'info', visible, onHide }) {
  useEffect(() => {
    if (visible && onHide) {
      const timer = setTimeout(onHide, 3000);
      return () => clearTimeout(timer);
    }
  }, [visible, onHide]);

  return (
    <div className={`toast toast--${type} ${visible ? 'toast--visible' : ''}`}>
      {type === 'success' && '✓ '}
      {type === 'error' && '✕ '}
      {message}
    </div>
  );
}
