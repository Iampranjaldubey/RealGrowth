import React from 'react';

export const Skeleton = ({ width = '100%', height = '20px', borderRadius = '8px', className = '' }) => {
  return (
    <div 
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius }}
    />
  );
};

export const ChartSkeleton = () => {
  return (
    <div className="glass-card stagger-children" style={{ height: '420px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
        <Skeleton width="40%" height="28px" />
        <Skeleton width="120px" height="32px" />
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: '4%' }}>
        {[...Array(12)].map((_, i) => (
          <Skeleton 
            key={i} 
            width="8%" 
            height={`${Math.max(20, Math.random() * 100)}%`} 
            borderRadius="4px 4px 0 0" 
          />
        ))}
      </div>
    </div>
  );
};

export const StatCardSkeleton = () => {
  return (
    <div className="glass-card">
      <Skeleton width="60%" height="20px" className="mb-4" />
      <Skeleton width="80%" height="36px" className="mb-2" />
      <Skeleton width="40%" height="16px" />
    </div>
  );
};
