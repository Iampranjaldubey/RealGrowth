import React, { useEffect, useState } from 'react';
import PageTransition from '../components/Layout/PageTransition';
import StatCard from '../components/UI/StatCard';
import ChartCard from '../components/UI/ChartCard';
import LineChart from '../components/Charts/LineChart';
import api from '../services/api';
import { chartColors } from '../utils/chartConfig';
import { formatCurrency, formatPercent, formatCompactNumber } from '../utils/formatters';

const Home = () => {
  const [dashboardData, setDashboardData] = useState({
    globalGDP: null,
    globalInflation: null,
    globalGrowth: null,
    loading: true,
    error: null
  });

  const [topMovers, setTopMovers] = useState({
    data: null,
    loading: true
  });

  // Fetch summary stats for the dashboard
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch some representative data for the top cards
        // For a real app, you might want specific summary endpoints
        // Here we'll fetch GDP data for a recent year (e.g., 2022) to calculate a global average
        const [gdpData, growthData] = await Promise.all([
          api.getGdpData('2022', 0),
          // Fetch US growth as a placeholder for a trend chart
          api.getGrowthByCountry('United States')
        ]);

        // Calculate a rough global average GDP from the top 10 returned
        let avgGdp = 0;
        if (gdpData.chart_data && gdpData.chart_data.length > 0) {
          avgGdp = gdpData.chart_data.reduce((a, b) => a + b, 0) / gdpData.chart_data.length;
        }

        setDashboardData({
          globalGDP: avgGdp,
          globalInflation: 8.7, // 2022 Global inflation approx
          globalGrowth: 3.2,    // 2022 Global growth approx
          loading: false,
          error: null
        });

        // Set up the trend chart
        if (growthData && growthData.years) {
          // Take last 10 years
          const recentYears = growthData.years.slice(-10);
          const recentValues = growthData.values.slice(-10);
          
          setTopMovers({
            labels: recentYears,
            values: recentValues,
            loading: false
          });
        }
      } catch (error) {
        console.error("Failed to load dashboard data", error);
        setDashboardData(prev => ({ ...prev, loading: false, error: error.message }));
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <PageTransition>
      <div className="page-header">
        <h1>Global Economic Overview</h1>
        <p>A comprehensive dashboard tracking key economic indicators across the world.</p>
      </div>

      <div className="stats-grid stagger-children">
        <StatCard 
          title="Avg GDP Per Capita (Top 10)" 
          value={dashboardData.globalGDP} 
          prefix="$"
          icon="💰"
          color="primary"
          loading={dashboardData.loading}
        />
        <StatCard 
          title="Global Inflation (2022 est)" 
          value={dashboardData.globalInflation} 
          suffix="%"
          icon="📈"
          color="warning"
          trend={{ value: 4.0, isPositive: false }} // High inflation is bad
          loading={dashboardData.loading}
        />
        <StatCard 
          title="Global Growth (2022 est)" 
          value={dashboardData.globalGrowth} 
          suffix="%"
          icon="🚀"
          color="tertiary"
          trend={{ value: 2.8, isPositive: false }}
          loading={dashboardData.loading}
        />
      </div>

      <div className="two-col-grid">
        <ChartCard 
          title="US Economic Growth Trend" 
          subtitle="Last 10 Years Real GDP Growth (%)"
          loading={topMovers.loading}
        >
          {topMovers.labels && (
            <LineChart 
              labels={topMovers.labels}
              datasets={[{
                label: 'US Growth',
                data: topMovers.values,
                gradientStart: chartColors.tertiary,
                gradientEnd: 'rgba(16, 185, 129, 0)',
                fill: true
              }]}
              yAxisFormatter={formatPercent}
              showLegend={false}
            />
          )}
        </ChartCard>

        <div className="glass-card stagger-children" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '16px' }}>Quick Navigation</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', flex: 1 }}>
            {[
              { path: '/correlation', label: 'Correlation Explorer', icon: '🔬', color: 'secondary' },
              { path: '/gdp', label: 'GDP Comparison', icon: '💰', color: 'primary' },
              { path: '/inflation', label: 'Inflation Trends', icon: '📈', color: 'warning' },
              { path: '/debt', label: 'Global Debt Map', icon: '🏦', color: 'danger' }
            ].map((link, i) => (
              <a 
                key={i} 
                href={link.path} 
                className="glass-card"
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  padding: '24px 16px',
                  textDecoration: 'none',
                  borderLeft: `3px solid var(--accent-${link.color})`,
                  gap: '12px',
                  transition: 'all 0.2s ease'
                }}
              >
                <span style={{ fontSize: '2rem' }}>{link.icon}</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 500, textAlign: 'center' }}>{link.label}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </PageTransition>
  );
};

export default Home;
