// hooks/useNews.js
import { useCallback, useEffect, useState } from 'react';
import { fetchNewsList } from '../lib/supabase';

export function useNews(filters = {}) {
  const { query = '', dirFilter = '', catFilter = '', sortAsc = false } = filters;
  const LIMIT = 50;
  
  const [newsList, setNewsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);

  const [totalCount, setTotalCount] = useState(0);

  const load = useCallback(async (isRefresh = false, isLoadMore = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else if (isLoadMore) setLoadingMore(true);
      else setLoading(true);

      const offset = isLoadMore ? (page + 1) * LIMIT : 0;
      const { data, count } = await fetchNewsList({ offset, limit: LIMIT, query, dirFilter, catFilter, sortAsc });

      if (isLoadMore) {
        setNewsList(prev => [...prev, ...(data ?? [])]);
        setPage(prev => prev + 1);
      } else {
        setNewsList(data ?? []);
        setTotalCount(count ?? 0);
        setPage(0);
      }
      
      setHasMore((data ?? []).length === LIMIT);
    } catch (e) {
      console.warn('[useNews] error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLoadingMore(false);
    }
  }, [page, query, dirFilter, catFilter, sortAsc]);

  // When filters change, reset and load from scratch
  useEffect(() => { 
    setHasMore(true);
    load(false, false); 
  }, [query, dirFilter, catFilter, sortAsc]);

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore && !loading && !refreshing) {
      load(false, true);
    }
  }, [loadingMore, hasMore, loading, refreshing, load]);

  return { newsList, totalCount, loading, refreshing, loadingMore, hasMore, loadMore, refetch: () => load(true, false) };
}
