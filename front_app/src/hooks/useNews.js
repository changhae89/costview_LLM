// hooks/useNews.js
import { useCallback, useEffect, useState } from 'react';
import { fetchNewsList } from '../lib/supabase';

export function useNews() {
  const [newsList, setNewsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      const data = await fetchNewsList();
      setNewsList(data ?? []);
    } catch (e) {
      console.warn('[useNews] error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { newsList, loading, refreshing, refetch: () => load(true) };
}
