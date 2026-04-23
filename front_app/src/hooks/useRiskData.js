// hooks/useRiskData.js
import { useCallback, useEffect, useState } from 'react';
import { fetchUnifiedDaily, fetchUnifiedMonthly } from '../lib/api';

export function useRiskData() {
  const [daily, setDaily] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      const [d, m] = await Promise.all([fetchUnifiedDaily(), fetchUnifiedMonthly()]);
      if (d?.length > 0) setDaily(d);
      if (m?.length > 0) setMonthly(m);
    } catch (e) {
      console.warn('[useRiskData] error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { daily, monthly, loading, refreshing, refetch: () => load(true) };
}
