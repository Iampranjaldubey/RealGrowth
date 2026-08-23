import React, { useState, useEffect } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import ChartCard from '../components/UI/ChartCard';
import LineChart from '../components/Charts/LineChart';
import CountrySelector from '../components/UI/CountrySelector';
import { useApi } from '../hooks/useApi';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatPercent } from '../utils/formatters';

const Inflation = () => {
  const [country, setCountry] = useState('United States');
  
  const { data, loading, error, execute } = useApi(api.getInflationByCountry);

  useEffect(() => {
    if (country) {
      execute(country);
    }
  }, [country]);

  // The inflation dataset in the backend only returns 15 years starting from 2008
  const years = Array.from({length: 15}, (_, i) => 2008 + i);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Inflation Rates</h1>
        <p>Explore inflation trends across different countries over time.</p>
      </div>

      <div className="controls-row glass-card" style={{ padding: '20px', marginBottom: '24px' }}>
        <CountrySelector 
          indicator="inflation" 
          value={country} 
          onChange={setCountry} 
          className="flex-1"
        />
      </div>

      <ChartCard 
        title={`Inflation Rate for ${country}`}
        subtitle="2008-2022"
        loading={loading}
        error={error}
      >
        {data && data.inflation && (
          <LineChart 
            labels={years}
            datasets={[{
              label: 'Inflation Rate',
              data: data.inflation,
              gradientStart: chartColors.warning,
              gradientEnd: 'rgba(245, 158, 11, 0)',
              fill: true,
              tension: 0.3
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

export default Inflation;
