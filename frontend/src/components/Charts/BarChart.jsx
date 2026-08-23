import React, { useRef, useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import { barChartConfig, createGradient } from '../../utils/chartConfig';

const BarChart = ({ 
  labels, 
  datasets, 
  title, 
  yAxisLabel,
  xAxisLabel,
  yAxisFormatter,
  showLegend = true,
  indexAxis = 'x' // 'y' for horizontal bar chart
}) => {
  const chartRef = useRef(null);
  const [chartData, setChartData] = useState({ labels: [], datasets: [] });

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const enrichedDatasets = datasets.map(dataset => {
      if (dataset.gradientStart && dataset.gradientEnd) {
        // Horizontal bar needs a different gradient direction (left to right)
        const gradient = indexAxis === 'y'
          ? chart.ctx.createLinearGradient(0, 0, 400, 0)
          : chart.ctx.createLinearGradient(0, 0, 0, 400);
          
        gradient.addColorStop(0, dataset.gradientStart);
        gradient.addColorStop(1, dataset.gradientEnd);
        
        return {
          ...dataset,
          backgroundColor: gradient,
          borderColor: dataset.gradientStart,
          borderWidth: 1,
        };
      }
      return dataset;
    });

    setChartData({
      labels,
      datasets: enrichedDatasets
    });
  }, [labels, datasets, indexAxis]);

  const options = {
    ...barChartConfig,
    indexAxis,
    plugins: {
      ...barChartConfig.plugins,
      title: {
        display: !!title,
        text: title,
        font: { size: 16, weight: 600, family: 'Inter' }
      },
      legend: {
        display: showLegend
      },
      tooltip: {
        ...barChartConfig.plugins.tooltip,
        callbacks: {
          label: (context) => {
            const val = indexAxis === 'y' ? context.parsed.x : context.parsed.y;
            let label = context.dataset.label || '';
            if (label) label += ': ';
            label += yAxisFormatter ? yAxisFormatter(val) : val;
            return label;
          }
        }
      }
    },
    scales: {
      ...barChartConfig.scales,
      y: {
        ...barChartConfig.scales.y,
        title: {
          display: indexAxis === 'x' && !!yAxisLabel,
          text: yAxisLabel
        },
        ticks: {
          ...barChartConfig.scales.y.ticks,
          callback: (value) => (indexAxis === 'x' && yAxisFormatter) ? yAxisFormatter(value) : value
        }
      },
      x: {
        ...barChartConfig.scales.x,
        title: {
          display: indexAxis === 'y' && !!xAxisLabel,
          text: xAxisLabel
        },
        ticks: {
          ...barChartConfig.scales.x.ticks,
          callback: (value) => (indexAxis === 'y' && yAxisFormatter) ? yAxisFormatter(value) : value
        }
      }
    }
  };

  return <Bar ref={chartRef} data={chartData} options={options} />;
};

export default BarChart;
