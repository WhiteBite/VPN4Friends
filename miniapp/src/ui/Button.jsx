import React from 'react';

export default function Button({ 
  children, 
  variant = 'primary', // primary | secondary | outline | ghost | icon
  isLoading = false, 
  className = '', 
  disabled, 
  style,
  ...props 
}) {
  let mappedVariant = variant;
  if (variant === 'secondary') mappedVariant = 'ghost';

  const cn = [
    variant !== 'custom' && (variant === 'icon' ? 'btn-icon' : 'btn'),
    variant !== 'icon' && variant !== 'custom' ? `btn--${mappedVariant}` : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <button 
      className={cn} 
      disabled={isLoading || disabled} 
      style={style}
      {...props}
    >
      {isLoading ? '...' : children}
    </button>
  );
}
