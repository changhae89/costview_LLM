// hooks/useDashboard.js
import { useCallback, useEffect, useState } from 'react';
import { fetchCausalChains, fetchDashboardMetrics, fetchNewsList } from '../lib/api';

export function useDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [chains, setChains] = useState([]);
  const [newsList, setNewsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      const [m, c, n] = await Promise.all([
        fetchDashboardMetrics(),
        fetchCausalChains(),
        fetchNewsList(),
      ]);
      setMetrics(m);
      setChains(c ?? []);
      setNewsList((n?.data ?? []).slice(0, 10));
    } catch (e) {
      console.warn('[useDashboard] error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { metrics, chains, newsList, loading, refreshing, refetch: () => load(true) };
}
