import React, { useEffect, useState } from 'react';
import { StatCardSkeleton } from './LoadingSkeleton';

const StatCard = ({ 
  title, 
  value, 
  prefix = '', 
  suffix = '', 
  trend = null, // e.g., { value: 5.2, isPositive: true }
  icon = null,
  loading = false,
  color = 'primary' // 'primary', 'secondary', 'tertiary', 'warning', 'danger'
}) => {
  const [displayValue, setDisplayValue] = useState(0);
  
  // Animated number counter effect
  useEffect(() => {
    if (loading || value === null || value === undefined || isNaN(value)) return;
    
    const target = Number(value);
    const duration = 1000; // ms
    const steps = 30;
    const stepTime = duration / steps;
    const increment = target / steps;
    
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
        clearInterval(timer);
        setDisplayValue(target);
      } else {
        setDisplayValue(current);
      }
    }, stepTime);
    
    return () => clearInterval(timer);
  }, [value, loading]);

  if (loading) {
    return <StatCardSkeleton />;
  }

  // Format the number depending on if it's a decimal or whole number
  const formattedValue = Number.isInteger(displayValue) 
    ? displayValue.toLocaleString()
    : displayValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const isPositiveTrend = trend?.isPositive ?? trend?.value > 0;
  const trendColor = isPositiveTrend ? 'var(--accent-tertiary)' : 'var(--accent-danger)';

  return (
    <div className="glass-card animate-fade-in-up" style={{ 
      position: 'relative',
      overflow: 'hidden',
      borderLeft: `4px solid var(--accent-${color})`
    }}>
      {/* Decorative gradient blob */}
      <div style={{
        position: 'absolute',
        top: '-50%',
        right: '-10%',
        width: '100px',
        height: '100px',
        background: `var(--accent-${color})`,
        filter: 'blur(50px)',
        opacity: 0.15,
        borderRadius: '50%'
      }} />
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>{title}</h4>
        {icon && <div style={{ fontSize: '1.2rem', opacity: 0.8 }}>{icon}</div>}
      </div>
      
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
          {prefix}{formattedValue}{suffix}
        </span>
      </div>
      
      {trend && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '12px', fontSize: '0.85rem' }}>
          <span style={{ 
            color: trendColor,
            display: 'flex',
            alignItems: 'center',
            background: `${trendColor}1A`,
            padding: '2px 6px',
            borderRadius: '4px',
            fontWeight: 600
          }}>
            {isPositiveTrend ? '↑' : '↓'} {Math.abs(trend.value)}%
          </span>
          <span style={{ color: 'var(--text-tertiary)' }}>
            vs previous year
          </span>
        </div>
      )}
    </div>
  );
};

export default StatCard;
