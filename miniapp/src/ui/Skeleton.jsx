import React from 'react';

/**
 * A pulsing placeholder component for loading states.
 * @param {string} type - 'text', 'box', 'circle', 'card'
 * @param {string} width - CSS width
 * @param {string} height - CSS height
 * @param {object} style - Extra styles
 * @param {string} className - Extra classes
 */
const Skeleton = ({ type = 'text', width, height, style, className = '' }) => {
  const baseClass = `skeleton skeleton--${type} ${className}`;
  const customStyle = {
    width: width || (type === 'text' ? '100%' : undefined),
    height: height || undefined,
    ...style
  };

  return <div className={baseClass} style={customStyle} />;
};

export default Skeleton;
