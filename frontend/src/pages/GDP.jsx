import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import BarChart from '../components/Charts/BarChart';
import LineChart from '../components/Charts/LineChart';
import YearSlider from '../components/UI/YearSlider';
import CountrySelector from '../components/UI/CountrySelector';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatCurrency, formatCompactNumber } from '../utils/formatters';

const GDP = () => {
  const [activeTab, setActiveTab] = useState('top10');
  
  // Top 10 State
  const [year, setYear] = useState(2022);
  const [population, setPopulation] = useState('0');
  
  // Compare State
  const [country1, setCountry1] = useState('United States');
  const [country2, setCountry2] = useState('China');

  // API Hooks
  const { data: gdpData, loading: gdpLoading, error: gdpError, execute: fetchGdp } = useApi(api.getGdpData);
  const { data: compareData, loading: compareLoading, error: compareError, execute: fetchCompare } = useApi(api.getGdpCompare);

  // Fetch Top 10
  useEffect(() => {
    if (activeTab === 'top10') {
      fetchGdp(year.toString(), population);
    }
  }, [year, population, activeTab]);

  // Fetch Compare
  useEffect(() => {
    if (activeTab === 'compare' && country1 && country2) {
      fetchCompare(country1, country2);
    }
  }, [country1, country2, activeTab]);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>GDP Per Capita</h1>
        <p>Analyze economic output per person across nations and time.</p>
      </div>

      <div className="tab-bar">
        <button 
          className={`tab-btn ${activeTab === 'top10' ? 'active' : ''}`}
          onClick={() => setActiveTab('top10')}
        >
          Top 10 Leaders
        </button>
        <button 
          className={`tab-btn ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
        >
          Country Comparison
        </button>
      </div>

      {activeTab === 'top10' && (
        <div className="animate-fade-in-up">
          <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
            <YearSlider 
              min={1960} 
              max={2023} 
              value={year} 
              onChange={setYear} 
            />
            
            <div className="form-group" style={{ minWidth: '200px' }}>
              <label>Minimum Population</label>
              <select value={population} onChange={(e) => setPopulation(e.target.value)}>
                <option value="0">All Countries</option>
                <option value="10000000">≥ 10 Million</option>
                <option value="50000000">≥ 50 Million</option>
                <option value="100000000">≥ 100 Million (10 Crore)</option>
                <option value="500000000">≥ 500 Million (50 Crore)</option>
                <option value="1000000000">≥ 1 Billion (100 Crore)</option>
              </select>
            </div>
          </div>

          <ChartCard 
            title={`Top 10 Highest GDP Per Capita (${year})`}
            loading={gdpLoading}
            error={gdpError}
          >
            {gdpData && gdpData.chart_labels && (
              <BarChart 
                indexAxis="y"
                labels={gdpData.chart_labels}
                datasets={[{
                  label: 'GDP Per Capita',
                  data: gdpData.chart_data,
                  gradientStart: chartColors.primary,
                  gradientEnd: chartColors.primaryLight,
                }]}
                xAxisLabel="USD"
                yAxisFormatter={formatCompactNumber}
              />
            )}
          </ChartCard>
        </div>
      )}

      {activeTab === 'compare' && (
        <div className="animate-fade-in-up">
          <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
            <CountrySelector 
              indicator="gdp" 
              value={country1} 
              onChange={setCountry1} 
              label="First Country"
            />
            <CountrySelector 
              indicator="gdp" 
              value={country2} 
              onChange={setCountry2} 
              label="Second Country"
            />
          </div>

          <ChartCard 
            title="Historical Comparison"
            loading={compareLoading}
            error={compareError}
          >
            {compareData && compareData.years && (
              <LineChart 
                labels={compareData.years}
                datasets={[
                  {
                    label: compareData.country1.name,
                    data: compareData.country1.data,
                    gradientStart: chartColors.primary,
                    gradientEnd: 'rgba(6, 182, 212, 0)',
                    fill: true
                  },
                  {
                    label: compareData.country2.name,
                    data: compareData.country2.data,
                    gradientStart: chartColors.secondary,
                    gradientEnd: 'rgba(139, 92, 246, 0)',
                    fill: true
                  }
                ]}
                yAxisLabel="USD"
                yAxisFormatter={formatCompactNumber}
              />
            )}
          </ChartCard>
        </div>
      )}
    </PageTransition>
  );
};

export default GDP;
