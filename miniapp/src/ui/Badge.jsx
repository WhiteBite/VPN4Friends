import React from 'react';

export default function Badge({ children, type = 'success', className = '', style, ...props }) {
  const cn = [
    'badge',
    type ? `badge--${type}` : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={cn} style={style} {...props}>
      {children}
    </div>
  );
}
