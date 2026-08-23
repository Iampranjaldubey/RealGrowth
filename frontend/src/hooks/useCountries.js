import { useState, useEffect } from 'react';
import api from '../services/api';

const CACHE = {};

/**
 * Hook to fetch and cache country lists for different indicators.
 */
export function useCountries(indicator) {
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    
    const fetchCountries = async () => {
      if (CACHE[indicator]) {
        if (isMounted) {
          setCountries(CACHE[indicator]);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      try {
        let result;
        switch (indicator) {
          case 'gdp':
            result = await api.getGdpCountries();
            break;
          case 'inflation':
            const resInf = await api.getInflationCountries();
            result = resInf.countries;
            break;
          case 'food':
            result = await api.getFoodCountries();
            break;
          case 'wages':
            result = await api.getWagesCountries();
            break;
          case 'growth':
            result = await api.getGrowthCountries();
            break;
          case 'population':
            const resPop = await api.getPopulationMetadata();
            result = resPop.countries;
            break;
          case 'correlation':
            result = await api.getCorrelationCountries();
            break;
          default:
            throw new Error(`Unknown indicator: ${indicator}`);
        }
        
        CACHE[indicator] = result;
        if (isMounted) {
          setCountries(result);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    if (indicator) {
      fetchCountries();
    }
    
    return () => {
      isMounted = false;
    };
  }, [indicator]);

  return { countries, loading, error };
}
