// lib/supabase.js
import 'react-native-url-polyfill/auto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

// ───── Queries ──────────────────────────────────────────────────

/** SCR-001 / SCR-004: indicator_daily_logs 최신 2건 (전일 대비 계산용) */
export async function fetchIndicatorLatest() {
  const { data, error } = await supabase
    .from('indicator_gpr_daily_logs')
    .select('ai_gpr_index, oil_disruptions, gpr_original, non_oil_gpr, reference_date')
    .order('reference_date', { ascending: false })
    .limit(2);
  if (error) throw error;
  return data ?? [];
}

/** SCR-004: 일간 전체 (최신 365건) */
export async function fetchIndicatorDaily() {
  const { data, error } = await supabase
    .from('indicator_gpr_daily_logs')
    .select('ai_gpr_index, oil_disruptions, gpr_original, non_oil_gpr, reference_date')
    .order('reference_date', { ascending: false })
    .limit(1250); // DB 전체 테이터(현재 1186개) 조회를 위해 1250으로 설정
  if (error) throw error;
  return (data ?? []).reverse();
}

/** SCR-004: 월간 전체 (최신 120건) */
export async function fetchIndicatorMonthly() {
  const { data, error } = await supabase
    .from('indicator_gpr_monthly_logs')
    .select('"AI_GPR_Index", oil_disruptions, gpr_original, non_oil_gpr, reference_date')
    .order('reference_date', { ascending: false })
    .limit(120);
  if (error) throw error;
  // 단일 쿼리용 필드 재설정 및 시간상 오름차순 역정렬
  return (data ?? []).reverse().map(d => ({
    ...d,
    ai_gpr_index: d['AI_GPR_Index'],
  }));
}

/** SCR-001: 카테고리별 가격 영향 */
export async function fetchCausalChains() {
  const { data, error } = await supabase
    .from('causal_chains')
    .select(`
      category, direction, magnitude,
      change_pct_min, change_pct_max,
      news_analyses!inner(reliability, created_at)
    `)
    .neq('direction', 'neutral')
    .gte('news_analyses.reliability', 0.3);
  if (error) throw error;
  return data ?? [];
}

/** SCR-003: 품목별 물가 예측 (causal_chains 전체) */
export async function fetchPredictions() {
  const { data, error } = await supabase
    .from('causal_chains')
    .select(`
      id, category, direction, magnitude,
      change_pct_min, change_pct_max,
      event, result, mechanism,
      monthly_impact,
      news_analyses!inner(
        id, summary, reliability, created_at,
        raw_news:raw_news_id(title, keyword, increased_items, decreased_items)
      )
    `)
    .gte('news_analyses.reliability', 0.3);
  if (error) throw error;
  return data ?? [];
}

/** SCR-002: 뉴스 목록 */
function getNthNonNullValue(rows, key, nth = 0) {
  let seen = 0;
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    const value = rows[i]?.[key];
    if (value === null || value === undefined || value === '') continue;
    if (seen === nth) return value;
    seen += 1;
  }
  return null;
}

function getNthNonNullRow(rows, key, nth = 0) {
  let seen = 0;
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    const value = rows[i]?.[key];
    if (value === null || value === undefined || value === '') continue;
    if (seen === nth) return rows[i];
    seen += 1;
  }
  return null;
}

export async function fetchNewsList() {
  const { data, error } = await supabase
    .from('news_analyses')
    .select(`
      id, summary, reliability, created_at,
      raw_news:raw_news_id(id, title, keyword, increased_items, decreased_items, is_deleted, origin_published_at, news_url),
      causal_chains(category, direction, magnitude)
    `)
    .gte('reliability', 0.3)
    .order('created_at', { ascending: false });
  if (error) throw error;
  return (data ?? []).filter(n => !n.raw_news?.is_deleted);
}

export async function fetchUnifiedDaily() {
  const safeQuery = async (table) => {
    try {
      const { data, error } = await supabase.from(table).select('*').order('reference_date', { ascending: false }).limit(1250);
      if (error) {
        console.warn(`[fetchUnifiedDaily] ${table} 조회 실패:`, error.message);
        return [];
      }
      return data ?? [];
    } catch (e) {
      console.warn(`[fetchUnifiedDaily] ${table} 예외:`, e.message);
      return [];
    }
  };

  const [gprData, ecosData, fredData] = await Promise.all([
    safeQuery('indicator_gpr_daily_logs'),
    safeQuery('indicator_ecos_daily_logs'),
    safeQuery('indicator_fred_daily_logs'),
  ]);

  const map = new Map();
  [gprData, ecosData, fredData].forEach(arr => {
    arr.forEach(item => {
      const d = item.reference_date;
      if (!d) return;
      if (!map.has(d)) map.set(d, { reference_date: d });
      Object.assign(map.get(d), item);
    });
  });
  return Array.from(map.values()).sort((a, b) => a.reference_date?.localeCompare(b.reference_date));
}

export async function fetchUnifiedMonthly() {
  const [gpr, ecos, fred, kosis] = await Promise.all([
    supabase.from('indicator_gpr_monthly_logs').select('*').order('reference_date', { ascending: false }).limit(120),
    supabase.from('indicator_ecos_monthly_logs').select('*').order('reference_date', { ascending: false }).limit(120),
    supabase.from('indicator_fred_monthly_logs').select('*').order('reference_month', { ascending: false }).limit(120),
    supabase.from('indicator_kosis_monthly_logs').select('*').order('reference_date', { ascending: false }).limit(120),
  ]);

  const map = new Map();
  
  const processArr = (arr, dateField) => {
    if (!arr) return;
    arr.forEach(item => {
      let d = item[dateField];
      if (!d) return;
      const monthPrefix = d.slice(0, 7);
      if (!map.has(monthPrefix)) map.set(monthPrefix, { reference_date: d });
      Object.assign(map.get(monthPrefix), item);
      // Ensure AI_GPR_Index mapped cleanly
      if (item['AI_GPR_Index'] !== undefined) {
        map.get(monthPrefix).ai_gpr_index = item['AI_GPR_Index'];
      }
    });
  };

  processArr(gpr.data, 'reference_date');
  processArr(ecos.data, 'reference_date');
  processArr(fred.data, 'reference_month');
  processArr(kosis.data, 'reference_date');

  return Array.from(map.values()).sort((a,b)=>a.reference_date?.localeCompare(b.reference_date));
}

export async function fetchDashboardMetrics() {
  const [d, m] = await Promise.all([
    fetchUnifiedDaily(),
    fetchUnifiedMonthly()
  ]);

  const rows = [...m, ...d].sort((a, b) => {
    const ad = a?.reference_date ?? '';
    const bd = b?.reference_date ?? '';
    return ad.localeCompare(bd);
  });

  const latestRow = rows[rows.length - 1] || {};
  const prevRow = rows[rows.length - 2] || {};
  const metricKeys = ['ai_gpr_index', 'krw_usd_rate', 'fred_wti', 'cpi_total', 'fred_treasury_10y'];

  const latestMetrics = Object.fromEntries(metricKeys.map(key => [key, getNthNonNullValue(rows, key, 0)]));
  const prevMetrics = Object.fromEntries(metricKeys.map(key => [key, getNthNonNullValue(rows, key, 1)]));
  const latestDates = Object.fromEntries(metricKeys.map(key => [key, getNthNonNullRow(rows, key, 0)?.reference_date ?? '']));
  const prevDates = Object.fromEntries(metricKeys.map(key => [key, getNthNonNullRow(rows, key, 1)?.reference_date ?? '']));

  return {
    latest: {
      ...latestRow,
      ...latestMetrics,
      dates: latestDates,
      ai_gpr_index: latestMetrics.ai_gpr_index ?? latestRow['AI_GPR_Index'] ?? latestRow.ai_gpr_index,
      reference_date: latestRow.reference_date,
    },
    prev: {
      ...prevRow,
      ...prevMetrics,
      dates: prevDates,
      ai_gpr_index: prevMetrics.ai_gpr_index ?? prevRow['AI_GPR_Index'] ?? prevRow.ai_gpr_index,
      reference_date: prevRow.reference_date,
    },
  };
}
