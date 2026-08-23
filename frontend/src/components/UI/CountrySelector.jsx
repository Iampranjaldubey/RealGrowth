import React from 'react';
import { useCountries } from '../../hooks/useCountries';

const CountrySelector = ({ 
  indicator, 
  value, 
  onChange, 
  id = 'country-select',
  label = 'Select Country',
  className = ''
}) => {
  const { countries, loading, error } = useCountries(indicator);

  return (
    <div className={`form-group ${className}`}>
      {label && <label htmlFor={id}>{label}</label>}
      
      <select 
        id={id}
        value={value} 
        onChange={(e) => onChange(e.target.value)}
        disabled={loading || error || countries.length === 0}
      >
        <option value="">
          {loading ? 'Loading countries...' : '-- Select a Country --'}
        </option>
        
        {countries.map(country => (
          <option key={country} value={country}>
            {country}
          </option>
        ))}
      </select>
      
      {error && <small style={{ color: 'var(--accent-danger)' }}>Failed to load countries</small>}
    </div>
  );
};

export default CountrySelector;
