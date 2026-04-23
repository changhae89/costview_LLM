// hooks/useNews.js
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchNewsList } from '../lib/supabase';

export function useNews(filters = {}) {
  const { query = '', dirFilter = '', catFilter = '', sortAsc = false } = filters;
  const LIMIT = 50;

  const [newsList, setNewsList] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  // ref로 페이지 관리 → stale closure / 중복 append 방지
  const pageRef = useRef(0);
  const hasMoreRef = useRef(true);
  const loadingMoreRef = useRef(false);
  const loadingRef = useRef(true);
  const refreshingRef = useRef(false);

  const load = useCallback(async ({ isRefresh = false, isLoadMore = false } = {}) => {
    if (isLoadMore && (!hasMoreRef.current || loadingMoreRef.current || loadingRef.current || refreshingRef.current)) return;

    if (isRefresh) { setRefreshing(true); refreshingRef.current = true; }
    else if (isLoadMore) { setLoadingMore(true); loadingMoreRef.current = true; }
    else { setLoading(true); loadingRef.current = true; }

    const offset = isLoadMore ? (pageRef.current + 1) * LIMIT : 0;

    try {
      const { data, count } = await fetchNewsList({ offset, limit: LIMIT, query, dirFilter, catFilter, sortAsc });
      const items = data ?? [];

      if (isLoadMore) {
        pageRef.current += 1;
        setNewsList(prev => {
          // ID 기반 중복 제거
          const existingIds = new Set(prev.map(n => n.id));
          const fresh = items.filter(n => !existingIds.has(n.id));
          return [...prev, ...fresh];
        });
      } else {
        pageRef.current = 0;
        setNewsList(items);
        setTotalCount(count ?? 0);
      }

      hasMoreRef.current = items.length === LIMIT;
      setHasMore(hasMoreRef.current);
    } catch (e) {
      console.warn('[useNews] error:', e);
    } finally {
      setLoading(false); loadingRef.current = false;
      setRefreshing(false); refreshingRef.current = false;
      setLoadingMore(false); loadingMoreRef.current = false;
    }
  }, [query, dirFilter, catFilter, sortAsc]); // page 제거 → stale closure 없음

  // 필터 변경 시 처음부터 재로드
  useEffect(() => {
    hasMoreRef.current = true;
    setHasMore(true);
    load({ isRefresh: false, isLoadMore: false });
  }, [query, dirFilter, catFilter, sortAsc]); // load 제거로 무한 루프 방지

  const loadMore = useCallback(() => {
    load({ isLoadMore: true });
  }, [load]);

  const refetch = useCallback(() => {
    load({ isRefresh: true });
  }, [load]);

  return { newsList, totalCount, loading, refreshing, loadingMore, hasMore, loadMore, refetch };
}

