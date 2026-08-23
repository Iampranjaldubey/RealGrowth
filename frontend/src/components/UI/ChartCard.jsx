import React from 'react';
import { ChartSkeleton } from './LoadingSkeleton';

const ChartCard = ({ 
  title, 
  subtitle,
  loading = false, 
  error = null, 
  children,
  className = ''
}) => {
  if (error) {
    return (
      <div className={`glass-card ${className}`} style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--accent-danger)', marginBottom: '8px', fontSize: '24px' }}>⚠️</div>
        <p style={{ color: 'var(--text-secondary)' }}>Failed to load chart data.</p>
        <small style={{ color: 'var(--text-tertiary)', marginTop: '4px' }}>{error}</small>
      </div>
    );
  }

  if (loading) {
    return <ChartSkeleton />;
  }

  return (
    <div className={`glass-card animate-fade-in-up ${className}`} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {(title || subtitle) && (
        <div style={{ marginBottom: '16px' }}>
          {title && <h3 style={{ fontSize: '1.25rem', marginBottom: '4px' }}>{title}</h3>}
          {subtitle && <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{subtitle}</p>}
        </div>
      )}
      <div style={{ flex: 1, position: 'relative' }}>
        {children}
      </div>
    </div>
  );
};

export default ChartCard;
