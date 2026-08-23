import { useState, useEffect } from 'react';
import axios from 'axios'; // We use raw axios to avoid interceptor cyclic deps or just use apiClient
import api from '../services/api';

/**
 * Custom hook for data fetching with loading and error states.
 */
export function useApi(apiFunc, initialData = null) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = async (...args) => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiFunc(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err.message || 'An error occurred');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, execute, setData };
}
