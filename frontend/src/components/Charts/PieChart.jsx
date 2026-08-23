import React from 'react';
import { Pie } from 'react-chartjs-2';
import { pieChartConfig } from '../../utils/chartConfig';

const PieChart = ({ 
  labels, 
  data, 
  title, 
  colors,
  formatter,
  isDoughnut = true
}) => {
  const chartData = {
    labels,
    datasets: [
      {
        data,
        backgroundColor: colors || [
          'rgba(6, 182, 212, 0.8)',   // Cyan
          'rgba(139, 92, 246, 0.8)',  // Purple
          'rgba(16, 185, 129, 0.8)',  // Emerald
          'rgba(245, 158, 11, 0.8)'   // Amber
        ],
        borderColor: colors || [
          '#06b6d4',
          '#8b5cf6',
          '#10b981',
          '#f59e0b'
        ],
        borderWidth: 1,
        hoverOffset: 10
      }
    ]
  };

  const options = {
    ...pieChartConfig,
    cutout: isDoughnut ? '65%' : '0%',
    plugins: {
      ...pieChartConfig.plugins,
      title: {
        display: !!title,
        text: title,
        font: { size: 16, weight: 600, family: 'Inter' }
      },
      tooltip: {
        ...pieChartConfig.plugins.tooltip,
        callbacks: {
          label: (context) => {
            const value = context.raw;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = Math.round((value / total) * 100);
            
            const formattedValue = formatter ? formatter(value) : value;
            return `${context.label}: ${formattedValue} (${percentage}%)`;
          }
        }
      }
    }
  };

  return <Pie data={chartData} options={options} />;
};

export default PieChart;
