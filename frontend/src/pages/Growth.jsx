import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import LineChart from '../components/Charts/LineChart';
import CountrySelector from '../components/UI/CountrySelector';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatPercent } from '../utils/formatters';

const Growth = () => {
  const [country, setCountry] = useState('United States');
  
  const { data, loading, error, execute } = useApi(api.getGrowthByCountry);

  useEffect(() => {
    if (country) {
      execute(country);
    }
  }, [country]);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Real Economic Growth</h1>
        <p>Monitor the rate of real GDP growth over time.</p>
      </div>

      <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
        <CountrySelector 
          indicator="growth" 
          value={country} 
          onChange={setCountry} 
          className="flex-1"
        />
      </div>

      <ChartCard 
        title={`Real Growth Rate: ${country}`}
        loading={loading}
        error={error}
      >
        {data && data.years && data.values && (
          <LineChart 
            labels={data.years}
            datasets={[{
              label: 'Growth Rate',
              data: data.values,
              gradientStart: chartColors.primary,
              gradientEnd: 'rgba(6, 182, 212, 0)',
              fill: true,
              tension: 0.2
            }]}
            yAxisLabel="%"
            yAxisFormatter={formatPercent}
            showLegend={false}
          />
        )}
      </ChartCard>
    </PageTransition>
  );
};

export default Growth;
