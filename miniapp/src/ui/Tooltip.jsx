import React, { useState, useRef, useEffect } from 'react';
import { IconInfo } from './Icons';

export default function Tooltip({ text, children, icon = true }) {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipRef = useRef(null);

  // Close tooltip if clicked outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target)) {
        setIsVisible(false);
      }
    }
    
    if (isVisible) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isVisible]);

  return (
    <div 
      className="tooltip-container" 
      ref={tooltipRef}
      style={{ display: 'inline-flex', alignItems: 'center', position: 'relative' }}
    >
      <div 
        onClick={(e) => {
          e.stopPropagation();
          setIsVisible(!isVisible);
        }}
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', cursor: 'help' }}
      >
        {children}
        {icon && (
          <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', opacity: 0.7 }}>
            <IconInfo />
          </span>
        )}
      </div>

      {isVisible && (
        <div 
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '8px',
            backgroundColor: 'var(--bg-elevated)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            padding: '8px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            width: 'max-content',
            maxWidth: '220px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: 100,
            pointerEvents: 'none',
            lineHeight: 1.4,
            whiteSpace: 'pre-wrap',
            textAlign: 'center'
          }}
        >
          {text}
          {/* Small Arrow indicator */}
          <div style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            borderWidth: '5px',
            borderStyle: 'solid',
            borderColor: 'var(--bg-elevated) transparent transparent transparent',
          }}></div>
        </div>
      )}
    </div>
  );
}
