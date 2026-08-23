import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import BarChart from '../components/Charts/BarChart';
import LineChart from '../components/Charts/LineChart';
import CountrySelector from '../components/UI/CountrySelector';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatCurrency } from '../utils/formatters';

const FoodPrices = () => {
  const [activeTab, setActiveTab] = useState('histogram');
  const [country1, setCountry1] = useState('United States');
  const [country2, setCountry2] = useState('United Kingdom');
  
  const { data: histData, loading: histLoading, error: histError, execute: fetchHist } = useApi(api.getFoodHistogram);
  const { data: lineData, loading: lineLoading, error: lineError, execute: fetchLine } = useApi(api.getFoodLine);

  useEffect(() => {
    if (country1 && country2) {
      if (activeTab === 'histogram') {
        fetchHist(country1, country2);
      } else {
        fetchLine(country1, country2);
      }
    }
  }, [country1, country2, activeTab]);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Food Prices</h1>
        <p>Explore and compare the cost of a healthy diet across different countries.</p>
      </div>

      <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
        <CountrySelector 
          indicator="food" 
          value={country1} 
          onChange={setCountry1} 
          label="First Country"
        />
        <CountrySelector 
          indicator="food" 
          value={country2} 
          onChange={setCountry2} 
          label="Second Country"
        />
      </div>

      <div className="tab-bar">
        <button 
          className={`tab-btn ${activeTab === 'histogram' ? 'active' : ''}`}
          onClick={() => setActiveTab('histogram')}
        >
          Bar Comparison
        </button>
        <button 
          className={`tab-btn ${activeTab === 'line' ? 'active' : ''}`}
          onClick={() => setActiveTab('line')}
        >
          Trend Line
        </button>
      </div>

      <ChartCard 
        title={`Food Price Comparison: ${country1} vs ${country2}`}
        subtitle="Recent 5 Years"
        loading={activeTab === 'histogram' ? histLoading : lineLoading}
        error={activeTab === 'histogram' ? histError : lineError}
      >
        {activeTab === 'histogram' && histData && (
          <BarChart 
            labels={histData.map(d => d.Year)}
            datasets={[
              {
                label: country1,
                data: histData.map(d => d[country1]),
                gradientStart: chartColors.primary,
                gradientEnd: chartColors.primaryLight,
              },
              {
                label: country2,
                data: histData.map(d => d[country2]),
                gradientStart: chartColors.secondary,
                gradientEnd: chartColors.secondaryLight,
              }
            ]}
            yAxisLabel="USD per day"
            yAxisFormatter={formatCurrency}
          />
        )}

        {activeTab === 'line' && lineData && (
          <LineChart 
            labels={lineData.map(d => d.Year)}
            datasets={[
              {
                label: country1,
                data: lineData.map(d => d[country1]),
                gradientStart: chartColors.primary,
                gradientEnd: 'rgba(6, 182, 212, 0)',
                fill: true
              },
              {
                label: country2,
                data: lineData.map(d => d[country2]),
                gradientStart: chartColors.secondary,
                gradientEnd: 'rgba(139, 92, 246, 0)',
                fill: true
              }
            ]}
            yAxisLabel="USD per day"
            yAxisFormatter={formatCurrency}
          />
        )}
      </ChartCard>
    </PageTransition>
  );
};

export default FoodPrices;
