import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import LineChart from '../components/Charts/LineChart';
import CountrySelector from '../components/UI/CountrySelector';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatCurrency } from '../utils/formatters';

const Wages = () => {
  const [country, setCountry] = useState('United States');
  
  const { data, loading, error, execute } = useApi(api.getWagesByCountry);

  useEffect(() => {
    if (country) {
      execute(country);
    }
  }, [country]);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Average Wages</h1>
        <p>Track historical average wage trends across different nations.</p>
      </div>

      <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
        <CountrySelector 
          indicator="wages" 
          value={country} 
          onChange={setCountry} 
          className="flex-1"
        />
      </div>

      <ChartCard 
        title={`Average Wages: ${country}`}
        loading={loading}
        error={error}
      >
        {data && Object.keys(data).length > 0 && (
          <LineChart 
            labels={Object.keys(data)}
            datasets={[{
              label: 'Average Wage',
              data: Object.values(data),
              gradientStart: chartColors.tertiary,
              gradientEnd: 'rgba(16, 185, 129, 0)',
              fill: true,
              tension: 0.2
            }]}
            yAxisLabel="USD"
            yAxisFormatter={formatCurrency}
            showLegend={false}
          />
        )}
      </ChartCard>
    </PageTransition>
  );
};

export default Wages;
