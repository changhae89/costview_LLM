import { supabase } from './supabase'

const BASE = import.meta.env.VITE_API_BASE_URL as string

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession()
  const token = session?.access_token

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    await supabase.auth.refreshSession()
    const { data: { session: next } } = await supabase.auth.getSession()
    if (!next) throw new Error('session_expired')
    return fetch(`${BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${next.access_token}`,
        ...options.headers,
      },
    })
  }
  return res
}

async function parseJson(res: Response) {
  const json = await res.json()
  if (!res.ok) throw new Error(json?.detail ?? json?.error ?? `HTTP ${res.status}`)
  return json?.data ?? json
}

function toQuery(params: Record<string, unknown>) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value == null || value === '' || value === false) return
    if (Array.isArray(value)) {
      value.forEach(v => q.append(key, String(v)))
      return
    }
    q.set(key, String(value))
  })
  const query = q.toString()
  return query ? `?${query}` : ''
}

export const dashboardApi = {
  kpi: () => apiFetch('/api/v1/dashboard/kpi').then(parseJson),
  pipelineStats: () => apiFetch('/api/v1/dashboard/pipeline-stats').then(parseJson),
  gprTrend: (days = 30) =>
    apiFetch(`/api/v1/dashboard/gpr-trend${toQuery({ days })}`).then(parseJson),
  causalSummary: () => apiFetch('/api/v1/dashboard/causal-summary').then(parseJson),
  recentAnalyses: (limit = 5) =>
    apiFetch(`/api/v1/dashboard/recent-analyses${toQuery({ limit })}`).then(parseJson),
}

export const newsApi = {
  raw: (page: number, pageSize: number, filters: {
    status?: string[]
    search?: string
    dateFrom?: string
    dateTo?: string
    showDeleted?: boolean
  }) => apiFetch(`/api/v1/news/raw${toQuery({
    page,
    page_size: pageSize,
    status: filters.status,
    search: filters.search,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    show_deleted: filters.showDeleted,
  })}`).then(parseJson),
  analyses: (page: number, pageSize: number) =>
    apiFetch(`/api/v1/news/analyses${toQuery({ page, page_size: pageSize })}`).then(parseJson),
}

export const causalApi = {
  list: (page: number, pageSize: number, filters: {
    category?: string
    direction?: string
    magnitude?: string
    transmissionMonths?: number
  }) => apiFetch(`/api/v1/causal/${toQuery({
    page,
    page_size: pageSize,
    category: filters.category,
    direction: filters.direction,
    magnitude: filters.magnitude,
    transmission_months: filters.transmissionMonths,
  })}`).then(parseJson),
  stats: () => apiFetch('/api/v1/causal/stats').then(parseJson),
}

export const indicatorApi = {
  series: (group: 'gpr' | 'ecos' | 'fred' | 'kosis', days?: number) =>
    apiFetch(`/api/v1/indicators/${group}${toQuery({ days })}`).then(parseJson),
}

export const categoryApi = {
  list: () => apiFetch('/api/v1/categories/').then(parseJson),
  create: (body: unknown) =>
    apiFetch('/api/v1/categories', { method: 'POST', body: JSON.stringify(body) }).then(parseJson),
  update: (code: string, body: unknown) =>
    apiFetch(`/api/v1/categories/${code}`, { method: 'PUT', body: JSON.stringify(body) }).then(parseJson),
  remove: (code: string) =>
    apiFetch(`/api/v1/categories/${code}`, { method: 'DELETE' }).then(parseJson),
}

export const consumerItemApi = {
  list: (showDeleted = false) =>
    apiFetch(`/api/v1/consumer-items/${toQuery({ show_deleted: showDeleted })}`).then(parseJson),
  create: (body: unknown) =>
    apiFetch('/api/v1/consumer-items', { method: 'POST', body: JSON.stringify(body) }).then(parseJson),
  update: (id: string, body: unknown) =>
    apiFetch(`/api/v1/consumer-items/${id}`, { method: 'PUT', body: JSON.stringify(body) }).then(parseJson),
  remove: (id: string) =>
    apiFetch(`/api/v1/consumer-items/${id}`, { method: 'DELETE' }).then(parseJson),
  restore: (id: string) =>
    apiFetch(`/api/v1/consumer-items/${id}/restore`, { method: 'POST' }).then(parseJson),
}
