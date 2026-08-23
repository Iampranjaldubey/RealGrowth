import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, LinearScale, PointElement, Tooltip, Legend } from 'chart.js';
import { Scatter } from 'react-chartjs-2';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import CountrySelector from '../components/UI/CountrySelector';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';

ChartJS.register(LinearScale, PointElement, Tooltip, Legend);

const Correlation = () => {
  const [country, setCountry] = useState('United States');
  const [indicator1, setIndicator1] = useState('gdp');
  const [indicator2, setIndicator2] = useState('inflation');
  
  const { data: indicators, loading: indLoading } = useApi(api.getCorrelationIndicators);
  const { data, loading, error, execute } = useApi(api.getCorrelation);

  // Fetch indicators on mount
  useEffect(() => {
    api.getCorrelationIndicators().catch(console.error);
  }, []);

  useEffect(() => {
    if (country && indicator1 && indicator2 && indicator1 !== indicator2) {
      execute(country, indicator1, indicator2);
    }
  }, [country, indicator1, indicator2]);

  // Prevent selecting the same indicator twice
  const handleInd1Change = (e) => {
    const val = e.target.value;
    setIndicator1(val);
    if (val === indicator2) {
      // Find another indicator to swap to
      const available = indicators?.indicators.map(i => i.id).filter(id => id !== val) || [];
      if (available.length > 0) setIndicator2(available[0]);
    }
  };

  const handleInd2Change = (e) => {
    const val = e.target.value;
    setIndicator2(val);
    if (val === indicator1) {
      const available = indicators?.indicators.map(i => i.id).filter(id => id !== val) || [];
      if (available.length > 0) setIndicator1(available[0]);
    }
  };

  // Generate Scatter Chart Data
  let scatterData = { datasets: [] };
  let scatterOptions = {};

  if (data && data.values1 && data.values2) {
    const points = data.values1.map((v, i) => ({
      x: v,
      y: data.values2[i],
      year: data.years[i]
    }));

    // Generate Regression Line points
    const minX = Math.min(...data.values1);
    const maxX = Math.max(...data.values1);
    const linePoints = [
      { x: minX, y: data.regression.slope * minX + data.regression.intercept },
      { x: maxX, y: data.regression.slope * maxX + data.regression.intercept }
    ];

    const ind1Name = indicators?.indicators.find(i => i.id === data.indicator1)?.name || data.indicator1;
    const ind2Name = indicators?.indicators.find(i => i.id === data.indicator2)?.name || data.indicator2;

    scatterData = {
      datasets: [
        {
          type: 'scatter',
          label: 'Data Points',
          data: points,
          backgroundColor: chartColors.primary,
          pointRadius: 6,
          pointHoverRadius: 8
        },
        {
          type: 'line',
          label: 'Trend (Linear Regression)',
          data: linePoints,
          borderColor: chartColors.secondary,
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }
      ]
    };

    scatterOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (context) => {
              if (context.dataset.type === 'line') return 'Trend Line';
              const point = context.raw;
              return `${point.year}: ${ind1Name}: ${point.x.toFixed(2)}, ${ind2Name}: ${point.y.toFixed(2)}`;
            }
          }
        }
      },
      scales: {
        x: { title: { display: true, text: ind1Name } },
        y: { title: { display: true, text: ind2Name } }
      }
    };
  }

  // Determine correlation strength text
  let correlationText = "";
  if (data?.correlation) {
    const absCorr = Math.abs(data.correlation);
    if (absCorr >= 0.7) correlationText = "Strong";
    else if (absCorr >= 0.4) correlationText = "Moderate";
    else correlationText = "Weak";
    
    correlationText += data.correlation > 0 ? " Positive" : " Negative";
    correlationText += " Correlation";
  }

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Correlation Explorer <span style={{ fontSize: '1rem', background: 'var(--accent-gradient)', padding: '4px 8px', borderRadius: '4px', color: 'white', verticalAlign: 'middle', marginLeft: '12px' }}>NEW</span></h1>
        <p>Analyze statistical relationships between different economic indicators.</p>
      </div>

      <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
        <CountrySelector 
          indicator="correlation" 
          value={country} 
          onChange={setCountry} 
          className="flex-1"
        />
        
        <div className="form-group" style={{ flex: 1 }}>
          <label>X-Axis Indicator</label>
          <select value={indicator1} onChange={handleInd1Change} disabled={indLoading}>
            {indicators?.indicators.map(ind => (
              <option key={ind.id} value={ind.id}>{ind.name}</option>
            ))}
          </select>
        </div>
        
        <div className="form-group" style={{ flex: 1 }}>
          <label>Y-Axis Indicator</label>
          <select value={indicator2} onChange={handleInd2Change} disabled={indLoading}>
            {indicators?.indicators.map(ind => (
              <option key={ind.id} value={ind.id}>{ind.name}</option>
            ))}
          </select>
        </div>
      </div>

      {error ? (
        <div className="glass-card" style={{ padding: '24px', textAlign: 'center', color: 'var(--accent-warning)' }}>
          <p>⚠️ {error}</p>
          <small>Try selecting a different country or indicators with overlapping years of data.</small>
        </div>
      ) : (
        <div className="two-col-grid">
          <ChartCard 
            title="Correlation Scatter Plot"
            loading={loading}
            className="col-span-2"
          >
            {data && <Scatter data={scatterData} options={scatterOptions} />}
          </ChartCard>

          {data && (
            <div className="glass-card animate-fade-in-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3>Statistical Analysis</h3>
              
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase' }}>Pearson Correlation (r)</p>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
                  <span style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {data.correlation.toFixed(3)}
                  </span>
                  <span style={{ 
                    padding: '4px 8px', 
                    borderRadius: '4px',
                    background: data.correlation > 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    color: data.correlation > 0 ? 'var(--accent-tertiary)' : 'var(--accent-danger)'
                  }}>
                    {correlationText}
                  </span>
                </div>
              </div>

              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase' }}>Overlapping Data</p>
                <p style={{ fontSize: '1.2rem', fontWeight: 500 }}>
                  {data.years.length} years ({Math.min(...data.years)} - {Math.max(...data.years)})
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </PageTransition>
  );
};

export default Correlation;
