import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import PieChart from '../components/Charts/PieChart';
import LineChart from '../components/Charts/LineChart';
import CountrySelector from '../components/UI/CountrySelector';
import YearSlider from '../components/UI/YearSlider';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatCompactNumber } from '../utils/formatters';

const Population = () => {
  const [activeTab, setActiveTab] = useState('distribution');
  const [country, setCountry] = useState('United States');
  const [year, setYear] = useState(2022);
  
  const { data: pieData, loading: pieLoading, error: pieError, execute: fetchPie } = useApi(api.getPopulationData);
  const { data: lineData, loading: lineLoading, error: lineError, execute: fetchLine } = useApi(api.getPopulationLine);

  useEffect(() => {
    if (country) {
      if (activeTab === 'distribution') {
        fetchPie(year.toString(), country);
      } else {
        fetchLine(country);
      }
    }
  }, [country, year, activeTab]);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Urban & Rural Population</h1>
        <p>Analyze demographic shifts between urban and rural areas.</p>
      </div>

      <div className="tab-bar">
        <button 
          className={`tab-btn ${activeTab === 'distribution' ? 'active' : ''}`}
          onClick={() => setActiveTab('distribution')}
        >
          Distribution (Pie)
        </button>
        <button 
          className={`tab-btn ${activeTab === 'trend' ? 'active' : ''}`}
          onClick={() => setActiveTab('trend')}
        >
          Historical Trend
        </button>
      </div>

      {activeTab === 'distribution' && (
        <div className="animate-fade-in-up">
          <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
            <CountrySelector 
              indicator="population" 
              value={country} 
              onChange={setCountry} 
            />
            <YearSlider 
              min={1960} 
              max={2022} 
              value={year} 
              onChange={setYear} 
            />
          </div>

          <div style={{ maxWidth: '600px', margin: '0 auto' }}>
            <ChartCard 
              title={`Population Distribution: ${country} (${year})`}
              loading={pieLoading}
              error={pieError}
            >
              {pieData && (
                <PieChart 
                  labels={['Urban Population', 'Rural Population']}
                  data={[pieData.urban, pieData.rural]}
                  colors={[chartColors.primary, chartColors.warning]}
                  formatter={formatCompactNumber}
                  isDoughnut={true}
                />
              )}
            </ChartCard>
          </div>
        </div>
      )}

      {activeTab === 'trend' && (
        <div className="animate-fade-in-up">
          <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
            <CountrySelector 
              indicator="population" 
              value={country} 
              onChange={setCountry} 
              className="flex-1"
            />
          </div>

          <div className="two-col-grid">
            <ChartCard 
              title="Urban Population Growth"
              loading={lineLoading}
              error={lineError}
            >
              {lineData && lineData.urban_population && (
                <LineChart 
                  labels={Object.keys(lineData.urban_population)}
                  datasets={[{
                    label: 'Urban Population',
                    data: Object.values(lineData.urban_population),
                    gradientStart: chartColors.primary,
                    gradientEnd: 'rgba(6, 182, 212, 0)',
                    fill: true
                  }]}
                  yAxisFormatter={formatCompactNumber}
                  showLegend={false}
                />
              )}
            </ChartCard>

            <ChartCard 
              title="Rural Population Trend"
              loading={lineLoading}
              error={lineError}
            >
              {lineData && lineData.rural_population && (
                <LineChart 
                  labels={Object.keys(lineData.rural_population)}
                  datasets={[{
                    label: 'Rural Population',
                    data: Object.values(lineData.rural_population),
                    gradientStart: chartColors.warning,
                    gradientEnd: 'rgba(245, 158, 11, 0)',
                    fill: true
                  }]}
                  yAxisFormatter={formatCompactNumber}
                  showLegend={false}
                />
              )}
            </ChartCard>
          </div>
        </div>
      )}
    </PageTransition>
  );
};

export default Population;
