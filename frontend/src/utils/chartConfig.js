import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Global defaults for dark mode / glassmorphism
ChartJS.defaults.color = '#94a3b8'; // text-secondary
ChartJS.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

const commonOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 20,
        font: { size: 12, weight: 500 }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.9)', // Deep bg
      titleColor: '#f1f5f9',
      bodyColor: '#cbd5e1',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      displayColors: true,
      boxPadding: 4,
    }
  }
};

const commonScales = {
  x: {
    grid: {
      color: 'rgba(255, 255, 255, 0.05)',
      drawBorder: false,
    },
    ticks: {
      font: { size: 11 }
    }
  },
  y: {
    grid: {
      color: 'rgba(255, 255, 255, 0.05)',
      drawBorder: false,
    },
    ticks: {
      font: { size: 11 }
    }
  }
};

export const lineChartConfig = {
  ...commonOptions,
  scales: commonScales,
  elements: {
    line: { tension: 0.3, borderWidth: 3 },
    point: { radius: 0, hitRadius: 10, hoverRadius: 6, hoverBorderWidth: 3 }
  }
};

export const barChartConfig = {
  ...commonOptions,
  scales: commonScales,
  elements: {
    bar: { borderRadius: 4, borderSkipped: false }
  }
};

export const pieChartConfig = {
  ...commonOptions,
  cutout: '65%',
  plugins: {
    ...commonOptions.plugins,
    legend: {
      position: 'bottom',
      labels: { usePointStyle: true, padding: 20 }
    }
  }
};

export const chartColors = {
  primary: '#06b6d4',
  primaryLight: 'rgba(6, 182, 212, 0.2)',
  secondary: '#8b5cf6',
  secondaryLight: 'rgba(139, 92, 246, 0.2)',
  tertiary: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  palette: [
    '#06b6d4', // Cyan
    '#8b5cf6', // Purple
    '#10b981', // Emerald
    '#f59e0b', // Amber
    '#ef4444', // Red
    '#ec4899', // Pink
    '#3b82f6', // Blue
  ]
};

export const createGradient = (ctx, colorStart, colorEnd) => {
  if (!ctx) return colorStart;
  const gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, colorStart);
  gradient.addColorStop(1, colorEnd || 'rgba(0,0,0,0)');
  return gradient;
};
