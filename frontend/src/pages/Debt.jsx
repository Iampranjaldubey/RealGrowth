import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import YearSlider from '../components/UI/YearSlider';
import WorldMap from '../components/Charts/WorldMap';
import { useApi } from '../hooks/useApi';
import api from '../services/api';

const Debt = () => {
  const [year, setYear] = useState(2022);
  const [tooltipContent, setTooltipContent] = useState(null);
  
  const { data, loading, error, execute } = useApi(api.getDebtData);

  useEffect(() => {
    execute(year.toString());
  }, [year]);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Debt-to-GDP Ratio</h1>
        <p>Global visualization of national debt levels relative to economic output.</p>
      </div>

      <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
        <YearSlider 
          min={1950} 
          max={2022} 
          value={year} 
          onChange={setYear} 
        />
      </div>

      <ChartCard 
        title={`Global Debt Map (${year})`}
        loading={loading}
        error={error}
        className="map-card"
      >
        {data && (
          <>
            <div style={{ height: '600px', width: '100%' }}>
              <WorldMap data={data} setTooltipContent={setTooltipContent} />
            </div>
            
            {/* Custom Tooltip */}
            {tooltipContent && (
              <div style={{
                position: 'fixed', // Simple fixed position for demo, ideally follows mouse
                top: '100px',
                right: '40px',
                background: 'rgba(15, 23, 42, 0.9)',
                color: 'var(--text-primary)',
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border-glass)',
                pointerEvents: 'none',
                zIndex: 1000,
                boxShadow: 'var(--shadow-lg)'
              }}>
                <div style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: '4px' }}>
                  {tooltipContent.name}
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>
                  Debt: <span style={{ color: 'white', fontWeight: 'bold' }}>{tooltipContent.value}</span>
                </div>
              </div>
            )}
          </>
        )}
      </ChartCard>
    </PageTransition>
  );
};

export default Debt;
