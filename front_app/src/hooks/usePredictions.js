// hooks/usePredictions.js
import { useCallback, useEffect, useState } from 'react';
import { fetchPredictions } from '../lib/api';

export function usePredictions() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [hasError, setHasError] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setHasError(false);
      const data = await fetchPredictions();
      if (data?.length > 0) setPredictions(data);
    } catch (e) {
      console.warn('[usePredictions] error:', e);
      setHasError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { predictions, loading, refreshing, hasError, refetch: () => load(true) };
}
