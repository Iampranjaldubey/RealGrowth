import React from 'react';

const YearSlider = ({ min, max, value, onChange, label = "Select Year" }) => {
  return (
    <div className="form-group" style={{ flex: 1, minWidth: '250px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '8px' }}>
        <label>{label}</label>
        <span style={{ 
          fontSize: '1.2rem', 
          fontWeight: 700, 
          color: 'var(--accent-primary)',
          fontVariantNumeric: 'tabular-nums'
        }}>
          {value}
        </span>
      </div>
      
      <div style={{ position: 'relative', padding: '10px 0' }}>
        <input 
          type="range" 
          min={min} 
          max={max} 
          value={value} 
          onChange={(e) => onChange(Number(e.target.value))}
          style={{
            width: '100%',
            accentColor: 'var(--accent-primary)',
            background: 'var(--bg-input)',
            height: '6px',
            borderRadius: '3px',
            outline: 'none',
            WebkitAppearance: 'none',
            appearance: 'none',
            cursor: 'pointer'
          }}
        />
        {/* Custom styling for the slider thumb is handled via CSS but accentColor covers most modern browsers */}
        
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginTop: '8px',
          color: 'var(--text-tertiary)',
          fontSize: '0.8rem',
          fontVariantNumeric: 'tabular-nums'
        }}>
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>
    </div>
  );
};

export default YearSlider;
