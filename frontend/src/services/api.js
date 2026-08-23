import axios from 'axios';

// Default to localhost:5000 in development, or relative path in production
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for generic error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    const customError = new Error(
      error.response?.data?.error || 'An unexpected error occurred while communicating with the server.'
    );
    customError.status = error.response?.status;
    return Promise.reject(customError);
  }
);

export const api = {
  // GDP
  getGdpData: (year, population) => apiClient.get('/gdp/data', { params: { year, population } }),
  getGdpCountries: () => apiClient.get('/gdp/countries'),
  getGdpCompare: (country1, country2) => apiClient.get('/gdp/compare', { params: { country1, country2 } }),
  
  // Inflation
  getInflationCountries: () => apiClient.get('/inflation/countries'),
  getInflationByCountry: (country) => apiClient.get(`/inflation/${country}`),
  
  // Food
  getFoodCountries: () => apiClient.get('/food/countries'),
  getFoodHistogram: (country1, country2) => apiClient.get('/food/histogram', { params: { country1, country2 } }),
  getFoodLine: (country1, country2) => apiClient.get('/food/line', { params: { country1, country2 } }),
  
  // Population
  getPopulationMetadata: () => apiClient.get('/population/metadata'),
  getPopulationData: (year, country) => apiClient.get('/population/', { params: { year, country } }),
  getPopulationLine: (country) => apiClient.get('/population/line', { params: { country } }),
  
  // Wages
  getWagesCountries: () => apiClient.get('/wages/countries'),
  getWagesByCountry: (country) => apiClient.get(`/wages/${country}`),
  
  // Debt
  getDebtData: (year) => apiClient.get('/debt/', { params: { year } }),
  
  // Growth
  getGrowthCountries: () => apiClient.get('/growth/countries'),
  getGrowthByCountry: (country) => apiClient.get(`/growth/${country}`),
  
  // Correlation
  getCorrelationIndicators: () => apiClient.get('/correlation/indicators'),
  getCorrelationCountries: () => apiClient.get('/correlation/countries'),
  getCorrelation: (country, indicator1, indicator2) => 
    apiClient.get('/correlation/', { params: { country, indicator1, indicator2 } }),
};

export default api;
