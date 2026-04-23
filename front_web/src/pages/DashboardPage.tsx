import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { dashboardApi } from '../lib/api'
import { formatCategory, DIRECTION_MAP } from '../constants/category'
import { formatDate, formatNumber } from '../lib/helpers'
import { ReliabilityBar } from '../components/ui/Badge'
import { COLORS } from '../constants/colors'

type MetricRow = Record<string, number | string | null>

function trendText(value: number | null, prev: number | null) {
  if (value == null || prev == null) return { label: '-', color: '#9CA3AF' }
  const diff = value - prev
  return {
    label: `${diff > 0 ? '+' : ''}${diff.toFixed(1)}`,
    color: diff >= 0 ? COLORS.up : COLORS.down,
  }
}

function KpiCard({
  label,
  value,
  prev,
  date,
  max,
  unit,
}: {
  label: string
  value: number | null
  prev: number | null
  date: string
  max: number
  unit?: string
}) {
  const pct = max > 0 ? Math.min(100, Math.max(4, ((value ?? 0) / max) * 100)) : 50
  const trend = trendText(value, prev)

  return (
    <div className="rounded-lg bg-white p-4 border border-gray-100">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <span className="font-mono text-[10px] text-gray-400">{date || '-'}</span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-gray-900">
        {value != null ? formatNumber(value) : '-'}
        {unit && <span className="ml-1 text-sm text-gray-400">{unit}</span>}
      </p>
      <div className="mt-3 h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 font-mono text-xs" style={{ color: trend.color }}>{trend.label}</p>
    </div>
  )
}

function first(rows: MetricRow[] | undefined, key: string) {
  return (rows?.[0]?.[key] as number | null | undefined) ?? null
}

function second(rows: MetricRow[] | undefined, key: string) {
  return (rows?.[1]?.[key] as number | null | undefined) ?? null
}

function dateOf(rows: MetricRow[] | undefined) {
  return (rows?.[0]?.reference_date as string | undefined) ?? ''
}

export function DashboardPage() {
  const { data: kpi } = useQuery({ queryKey: ['kpi'], queryFn: dashboardApi.kpi })
  const { data: riskTrend } = useQuery({ queryKey: ['globalRiskTrend'], queryFn: () => dashboardApi.gprTrend(30) })
  const { data: causal } = useQuery({ queryKey: ['causalSum'], queryFn: dashboardApi.causalSummary })
  const { data: news } = useQuery({ queryKey: ['recentNews'], queryFn: () => dashboardApi.recentAnalyses(6) })

  const causalGrouped = useMemo(() => Object.values(
    ((causal ?? []) as Record<string, unknown>[]).reduce((acc: Record<string, { category: string; up: number; down: number; neutral: number }>, row) => {
      const category = row.category as string
      if (!acc[category]) acc[category] = { category, up: 0, down: 0, neutral: 0 }
      const direction = (row.direction as string) ?? 'neutral'
      if (direction in acc[category]) acc[category][direction as 'up' | 'down' | 'neutral'] += 1
      return acc
    }, {})
  ).sort((a, b) => (b.up + b.down) - (a.up + a.down)).slice(0, 8), [causal])

  const highReliabilityCount = ((news ?? []) as Record<string, unknown>[]).filter(item => (item.reliability as number) >= 0.8).length

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">대시보드</h1>
        <p className="mt-1 text-xs text-gray-500">핵심 위험 지표와 최신 분석 흐름을 한 번에 확인합니다.</p>
      </div>

      <div className="grid grid-cols-5 gap-3">
        <KpiCard label="글로벌 위험지수" value={first(kpi?.global_risk, 'ai_gpr_index')} prev={second(kpi?.global_risk, 'ai_gpr_index')} date={dateOf(kpi?.global_risk)} max={300} />
        <KpiCard label="원/달러 환율" value={first(kpi?.exchange_rate, 'krw_usd_rate')} prev={second(kpi?.exchange_rate, 'krw_usd_rate')} date={dateOf(kpi?.exchange_rate)} max={2000} unit="원" />
        <KpiCard label="WTI 원유" value={first(kpi?.wti, 'fred_wti')} prev={second(kpi?.wti, 'fred_wti')} date={dateOf(kpi?.wti)} max={150} unit="$" />
        <KpiCard label="한국 소비자물가" value={first(kpi?.cpi, 'cpi_total')} prev={second(kpi?.cpi, 'cpi_total')} date={dateOf(kpi?.cpi)} max={10} unit="%" />
        <KpiCard label="미 10년 국채" value={first(kpi?.treasury_10y, 'fred_treasury_10y')} prev={second(kpi?.treasury_10y, 'fred_treasury_10y')} date={dateOf(kpi?.treasury_10y)} max={8} unit="%" />
      </div>

      <div className="grid grid-cols-[1.1fr_0.9fr] gap-4">
        <div className="rounded-lg bg-white p-5 border border-gray-100">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">글로벌 위험지수 30일 추이</p>
            <span className="text-xs text-gray-400">{(riskTrend ?? []).length.toLocaleString()} points</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={riskTrend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
              <XAxis dataKey="reference_date" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} width={40} />
              <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} />
              <Line type="monotone" dataKey="ai_gpr_index" stroke={COLORS.primary} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg bg-white p-5 border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">분석 품질</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-surface p-4">
              <p className="text-xs text-gray-500">최신 분석</p>
              <p className="mt-2 font-mono text-2xl font-semibold text-gray-900">{((news ?? []) as unknown[]).length}</p>
            </div>
            <div className="rounded-lg bg-surface p-4">
              <p className="text-xs text-gray-500">고신뢰 분석</p>
              <p className="mt-2 font-mono text-2xl font-semibold text-gray-900">{highReliabilityCount}</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {((news ?? []) as Record<string, unknown>[]).slice(0, 3).map(item => (
              <div key={item.id as string} className="border-t border-gray-100 pt-3 first:border-t-0 first:pt-0">
                <p className="line-clamp-2 text-xs font-medium text-gray-800">{item.summary as string}</p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-gray-400">{formatDate(item.created_at as string)}</span>
                  <ReliabilityBar value={item.reliability as number} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-[0.95fr_1.05fr] gap-4">
        <div className="rounded-lg bg-white p-5 border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">카테고리별 영향 방향</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart layout="vertical" data={causalGrouped} margin={{ left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F3F4F6" />
              <XAxis type="number" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <YAxis type="category" dataKey="category" tickFormatter={formatCategory} tick={{ fontSize: 10 }} width={80} />
              <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} />
              <Bar dataKey="up" stackId="a" fill={COLORS.up} radius={[0, 3, 3, 0]} />
              <Bar dataKey="down" stackId="a" fill={COLORS.down} />
              <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg bg-white p-5 border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">최신 분석 뉴스</p>
          <ul className="space-y-3">
            {((news ?? []) as Record<string, unknown>[]).map(item => {
              const chains = (item.causal_chains as { direction?: string }[]) ?? []
              const direction = chains[0]?.direction ?? 'neutral'
              const directionStyle = DIRECTION_MAP[direction]
              return (
                <li key={item.id as string} className="border-b border-gray-50 pb-3 last:border-0 last:pb-0">
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5 text-xs font-bold" style={{ color: directionStyle?.color }}>{directionStyle?.label.split(' ')[0]}</span>
                    <p className="flex-1 text-xs font-medium text-gray-800 line-clamp-2">{item.summary as string}</p>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
