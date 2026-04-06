import React from 'react';

/**
 * A premium loading spinner.
 * @param {'sm' | 'md' | 'lg'} size - Spinner size
 * @param {boolean} overlay - Whether to show as a full-screen overlay
 * @param {string} text - Optional text to show with the overlay
 * @param {string} className - Extra classes
 */
const Spinner = ({ size = 'md', overlay = false, text, className = '' }) => {
  const sizeClass = size !== 'md' ? `spinner--${size}` : '';
  const baseClass = `spinner ${sizeClass} ${className}`;

  if (overlay) {
    return (
      <div className="spinner--overlay">
        <div className={baseClass} />
        {text && <div className="spinner-text">{text}</div>}
      </div>
    );
  }

  return <div className={baseClass} />;
};

export default Spinner;
