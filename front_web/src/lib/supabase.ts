import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// ── Dashboard ──────────────────────────────────────────
export async function fetchKpiLatest() {
  const [gpr, ecos, fred, kosis] = await Promise.all([
    supabase.from('indicator_gpr_daily_logs')
      .select('ai_gpr_index, reference_date')
      .order('reference_date', { ascending: false }).limit(2),
    supabase.from('indicator_ecos_daily_logs')
      .select('krw_usd_rate, reference_date')
      .order('reference_date', { ascending: false }).limit(2),
    supabase.from('indicator_fred_daily_logs')
      .select('fred_wti, fred_treasury_10y, reference_date')
      .order('reference_date', { ascending: false }).limit(2),
    supabase.from('indicator_kosis_monthly_logs')
      .select('cpi_total, reference_date')
      .order('reference_date', { ascending: false }).limit(2),
  ])
  return { gpr: gpr.data ?? [], ecos: ecos.data ?? [], fred: fred.data ?? [], kosis: kosis.data ?? [] }
}

export async function fetchPipelineStats() {
  const { data } = await supabase
    .from('raw_news')
    .select('processing_status')
  const counts: Record<string, number> = { processed: 0, skipped: 0, pending: 0, failed: 0 }
  ;(data ?? []).forEach((r: { processing_status: string | null }) => {
    const s = r.processing_status ?? 'pending'
    counts[s] = (counts[s] ?? 0) + 1
  })
  return counts
}

export async function fetchGprTrend(days = 30) {
  const from = new Date()
  from.setDate(from.getDate() - days)
  const { data } = await supabase
    .from('indicator_gpr_daily_logs')
    .select('ai_gpr_index, reference_date')
    .gte('reference_date', from.toISOString().slice(0, 10))
    .order('reference_date', { ascending: true })
  return data ?? []
}

export async function fetchCausalSummary() {
  const { data } = await supabase
    .from('causal_chains')
    .select('category, direction, magnitude, news_analysis_id')
  return data ?? []
}

export async function fetchRecentAnalyses(limit = 5) {
  const { data } = await supabase
    .from('news_analyses')
    .select('id, summary, reliability, created_at, raw_news:raw_news_id(title, origin_published_at), causal_chains(category, direction)')
    .order('created_at', { ascending: false })
    .limit(limit)
  return data ?? []
}

// ── News ───────────────────────────────────────────────
export async function fetchRawNews(page: number, pageSize: number, filters: {
  status?: string[]
  search?: string
  dateFrom?: string
  dateTo?: string
  showDeleted?: boolean
}) {
  let q = supabase
    .from('raw_news')
    .select('id,title,news_url,processing_status,keyword,increased_items,decreased_items,origin_published_at,retry_count,is_deleted', { count: 'estimated' })
    .order('created_at', { ascending: false })
    .range(page * pageSize, (page + 1) * pageSize - 1)

  if (!filters.showDeleted) q = q.eq('is_deleted', false)
  if (filters.status?.length) q = q.in('processing_status', filters.status)
  if (filters.search) q = q.ilike('title', `%${filters.search}%`)
  if (filters.dateFrom) q = q.gte('origin_published_at', filters.dateFrom)
  if (filters.dateTo)   q = q.lte('origin_published_at', filters.dateTo)

  const { data, count } = await q
  return { data: data ?? [], total: count ?? 0 }
}

export async function fetchAnalyses(page: number, pageSize: number) {
  const { data, count } = await supabase
    .from('news_analyses')
    .select('id,summary,reliability,time_horizon,geo_scope,korea_relevance,created_at,effect_chain,reliability_reason,raw_news_id', { count: 'estimated' })
    .order('created_at', { ascending: false })
    .range(page * pageSize, (page + 1) * pageSize - 1)
  return { data: data ?? [], total: count ?? 0 }
}

export async function fetchAnalysisCausalChains(newsAnalysisId: string) {
  const { data } = await supabase
    .from('causal_chains')
    .select('*')
    .eq('news_analysis_id', newsAnalysisId)
  return data ?? []
}

// ── Causal Chains ──────────────────────────────────────
export async function fetchCausalChains(page: number, pageSize: number, filters: {
  category?: string
  direction?: string
  magnitude?: string
  transmissionMonths?: number
}) {
  let q = supabase
    .from('causal_chains')
    .select(`
      id, event, category, direction, magnitude,
      raw_shock_percent, wallet_hit_percent, transmission_time_months,
      mechanism, logic_steps, raw_shock_factors, wallet_hit_factors, transmission_rationale,
      news_analyses!inner(id, reliability, created_at, summary)
    `, { count: 'estimated' })
    .order('id', { ascending: false })
    .range(page * pageSize, (page + 1) * pageSize - 1)

  if (filters.category)  q = q.eq('category', filters.category)
  if (filters.direction) q = q.eq('direction', filters.direction)
  if (filters.magnitude) q = q.eq('magnitude', filters.magnitude)
  if (filters.transmissionMonths) q = q.eq('transmission_time_months', filters.transmissionMonths)

  const { data, count } = await q
  return { data: data ?? [], total: count ?? 0 }
}

export async function fetchCausalStats() {
  const { data } = await supabase
    .from('causal_chains')
    .select('category, direction, magnitude, raw_shock_percent, wallet_hit_percent, transmission_time_months')
  return data ?? []
}

// ── Indicators ────────────────────────────────────────
export async function fetchIndicatorData(table: string, columns: string, days?: number) {
  let q = supabase.from(table).select(columns).order('reference_date', { ascending: true })
  if (days) {
    const from = new Date()
    from.setDate(from.getDate() - days)
    q = q.gte('reference_date', from.toISOString().slice(0, 10))
  }
  const { data } = await q.limit(2000)
  return data ?? []
}

// ── Categories ────────────────────────────────────────
export async function fetchCategories() {
  const { data } = await supabase
    .from('cost_categories')
    .select('*')
    .order('sort_order', { ascending: true })
  return data ?? []
}

// ── Consumer Items ────────────────────────────────────
export async function fetchConsumerItems(showDeleted = false) {
  let q = supabase.from('consumer_items').select('*').order('created_at', { ascending: false })
  if (!showDeleted) q = q.eq('is_deleted', false)
  const { data } = await q
  return data ?? []
}
