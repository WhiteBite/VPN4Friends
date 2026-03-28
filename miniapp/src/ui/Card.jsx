import React from 'react';

export default function Card({ children, className = '', hero = false, style, ...props }) {
  const cn = [
    'card',
    hero ? 'card--hero' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <section className={cn} style={style} {...props}>
      {children}
    </section>
  );
}
