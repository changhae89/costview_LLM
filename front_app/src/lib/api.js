const DEFAULT_API_BASE_URL = 'http://localhost:8020';

const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  process.env.VITE_API_BASE_URL ??
  DEFAULT_API_BASE_URL
).replace(/\/$/, '');

function toQuery(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

async function apiFetch(path, params) {
  const url = `${API_BASE_URL}${path}${toQuery(params)}`;
  const response = await fetch(url);

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`API ${response.status}: ${message || url}`);
  }

  return response.json();
}

export async function fetchDashboardMetrics() {
  return apiFetch('/api/v1/mobile/dashboard-metrics');
}

export async function fetchCausalChains() {
  return apiFetch('/api/v1/mobile/causal-chains');
}

export async function fetchNewsList({
  offset = 0,
  limit = 50,
  query = '',
  dirFilter = '',
  catFilter = '',
  sortAsc = false,
} = {}) {
  return apiFetch('/api/v1/mobile/news', {
    offset,
    limit,
    query,
    dir_filter: dirFilter,
    cat_filter: catFilter,
    sort_asc: sortAsc,
  });
}

export async function fetchPredictions() {
  return apiFetch('/api/v1/mobile/predictions');
}

export async function fetchUnifiedDaily() {
  return apiFetch('/api/v1/mobile/indicators/daily');
}

export async function fetchUnifiedMonthly() {
  return apiFetch('/api/v1/mobile/indicators/monthly');
}
