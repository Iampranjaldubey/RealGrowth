/**
 * Format a number as currency (USD)
 */
export const formatCurrency = (value, decimals = 0) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

/**
 * Format a number as a percentage
 */
export const formatPercent = (value, decimals = 2) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  // If the API returns 5 for 5%, we append %. If it returns 0.05, we'd multiply by 100.
  // Assuming the API returns the exact number to be displayed.
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value) + '%';
};

/**
 * Format a large number with abbreviations (K, M, B)
 */
export const formatCompactNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(value);
};

/**
 * Standard number formatting with commas
 */
export const formatNumber = (value, decimals = 0) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};
