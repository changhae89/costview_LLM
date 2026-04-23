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

  const load = useCallback(async (isRefresh = false, loadPage = 0) => {
    const isLoadMore = loadPage > 0;
    try {
      if (isRefresh) setRefreshing(true);
      else if (isLoadMore) setLoadingMore(true);
      else setLoading(true);

      const offset = loadPage * LIMIT;
      const { data, count } = await fetchNewsList({ offset, limit: LIMIT, query, dirFilter, catFilter, sortAsc });

      if (isLoadMore) {
        setNewsList(prev => [...prev, ...(data ?? [])]);
        setPage(loadPage);
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
  }, [query, dirFilter, catFilter, sortAsc]);

  // When filters change, reset and load from scratch
  useEffect(() => { 
    setHasMore(true);
    load(false, 0); 
  }, [load]);

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore && !loading && !refreshing) {
      load(false, page + 1);
    }
  }, [loadingMore, hasMore, loading, refreshing, load, page]);

  const refetch = useCallback(() => load(true, 0), [load]);

  return { newsList, totalCount, loading, refreshing, loadingMore, hasMore, loadMore, refetch };
}
