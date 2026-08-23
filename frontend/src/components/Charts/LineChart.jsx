import React, { useRef, useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { lineChartConfig, createGradient } from '../../utils/chartConfig';

const LineChart = ({ 
  labels, 
  datasets, 
  title, 
  yAxisLabel,
  xAxisLabel = 'Year',
  yAxisFormatter,
  showLegend = true
}) => {
  const chartRef = useRef(null);
  const [chartData, setChartData] = useState({ labels: [], datasets: [] });

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Apply gradients if dataset provides color strings instead of raw colors
    const enrichedDatasets = datasets.map(dataset => {
      if (dataset.gradientStart && dataset.gradientEnd) {
        const gradient = createGradient(chart.ctx, dataset.gradientStart, dataset.gradientEnd);
        return {
          ...dataset,
          backgroundColor: gradient,
          borderColor: dataset.gradientStart,
        };
      }
      return dataset;
    });

    setChartData({
      labels,
      datasets: enrichedDatasets
    });
  }, [labels, datasets]);

  const options = {
    ...lineChartConfig,
    plugins: {
      ...lineChartConfig.plugins,
      title: {
        display: !!title,
        text: title,
        font: { size: 16, weight: 600, family: 'Inter' },
        padding: { bottom: 20 }
      },
      legend: {
        display: showLegend,
        position: 'top'
      },
      tooltip: {
        ...lineChartConfig.plugins.tooltip,
        callbacks: {
          label: (context) => {
            let label = context.dataset.label || '';
            if (label) label += ': ';
            
            const val = context.parsed.y;
            label += yAxisFormatter ? yAxisFormatter(val) : val;
            return label;
          }
        }
      }
    },
    scales: {
      ...lineChartConfig.scales,
      y: {
        ...lineChartConfig.scales.y,
        title: {
          display: !!yAxisLabel,
          text: yAxisLabel
        },
        ticks: {
          ...lineChartConfig.scales.y.ticks,
          callback: (value) => yAxisFormatter ? yAxisFormatter(value) : value
        }
      },
      x: {
        ...lineChartConfig.scales.x,
        title: {
          display: !!xAxisLabel,
          text: xAxisLabel
        }
      }
    }
  };

  return <Line ref={chartRef} data={chartData} options={options} />;
};

export default LineChart;
