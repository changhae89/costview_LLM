import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, CartesianGrid } from 'recharts'
import { dashboardApi } from '../lib/api'
import { formatCategory, DIRECTION_MAP } from '../constants/category'
import { formatDate, formatNumber } from '../lib/helpers'
import { ReliabilityBar } from '../components/ui/Badge'
import { COLORS } from '../constants/colors'

const PAGE_TITLE = '대시보드'

function KpiCard({ label, value, prev, date, max, unit }: {
  label: string; value: number | null; prev: number | null
  date: string; max: number; unit?: string
}) {
  const diff = (value ?? 0) - (prev ?? 0)
  const pct = max > 0 ? Math.min(100, Math.max(4, ((value ?? 0) / max) * 100)) : 50
  const gaugeColor = pct < 25 ? '#60A5FA' : pct < 50 ? '#FBBF24' : pct < 75 ? '#F97316' : '#EF4444'
  const diffColor = diff > 0 ? COLORS.up : COLORS.down

  return (
    <div className="relative rounded-xl bg-white p-5 shadow-sm border border-gray-100 animate-fade-in-up overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full bg-primary rounded-l-xl" />
      <p className="text-xs font-medium text-gray-500 mb-1 ml-1">{label}</p>
      <p className="font-mono text-2xl font-medium tabular-nums text-gray-900 ml-1">
        {value != null ? formatNumber(value) : '-'}
        {unit && <span className="text-sm text-gray-400 ml-1">{unit}</span>}
      </p>
      <div className="my-2 h-1.5 rounded-full bg-gray-100 overflow-hidden ml-1">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: gaugeColor }} />
      </div>
      <div className="flex items-center justify-between ml-1">
        <span className="font-mono text-xs" style={{ color: diffColor }}>
          {diff > 0 ? '▲' : '▼'}{Math.abs(diff).toFixed(1)}
        </span>
        <span className="font-mono text-[10px] text-gray-400">{date}</span>
      </div>
    </div>
  )
}

const PIPE_COLORS: Record<string, string> = {
  processed: '#1D9E75', skipped: '#9CA3AF', pending: '#EF9F27', failed: '#D85A30',
}

export function DashboardPage() {
  const { data: kpi }      = useQuery({ queryKey: ['kpi'],      queryFn: dashboardApi.kpi })
  const { data: pipe }     = useQuery({ queryKey: ['pipeline'], queryFn: dashboardApi.pipelineStats })
  const { data: gprTrend } = useQuery({ queryKey: ['gprTrend'], queryFn: () => dashboardApi.gprTrend(30) })
  const { data: causal }   = useQuery({ queryKey: ['causalSum'],queryFn: dashboardApi.causalSummary })
  const { data: news }     = useQuery({ queryKey: ['recentNews'],queryFn: () => dashboardApi.recentAnalyses(5) })

  const g0 = kpi?.gpr[0]; const g1 = kpi?.gpr[1]
  const e0 = kpi?.ecos[0]; const e1 = kpi?.ecos[1]
  const f0 = kpi?.fred[0]; const f1 = kpi?.fred[1]
  const k0 = kpi?.kosis[0]; const k1 = kpi?.kosis[1]

  const pipeData = pipe ? Object.entries(pipe as Record<string, number>).map(([name, value]) => ({ name, value })) : []

  const causalGrouped = Object.values(
    ((causal ?? []) as Record<string, unknown>[]).reduce((acc: Record<string, { category: string; up: number; down: number; neutral: number }>, c) => {
      const cat = c.category as string
      if (!acc[cat]) acc[cat] = { category: cat, up: 0, down: 0, neutral: 0 }
      const dir = (c.direction as string) ?? 'neutral'
      if (dir in acc[cat]) acc[cat][dir as 'up' | 'down' | 'neutral']++
      return acc
    }, {})
  ).sort((a: { up: number; down: number }, b: { up: number; down: number }) => (b.up + b.down) - (a.up + a.down)).slice(0, 8)

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">{PAGE_TITLE}</h1>

      {/* KPI 카드 */}
      <div className="grid grid-cols-5 gap-4">
        <KpiCard label="글로벌 위기 지수" value={g0?.ai_gpr_index ?? null} prev={g1?.ai_gpr_index ?? null} date={g0?.reference_date ?? ''} max={300} />
        <KpiCard label="원/달러 환율" value={e0?.krw_usd_rate ?? null} prev={e1?.krw_usd_rate ?? null} date={e0?.reference_date ?? ''} max={2000} unit="₩" />
        <KpiCard label="WTI 원유" value={f0?.fred_wti ?? null} prev={f1?.fred_wti ?? null} date={f0?.reference_date ?? ''} max={150} unit="$" />
        <KpiCard label="한국 소비자물가" value={k0?.cpi_total ?? null} prev={k1?.cpi_total ?? null} date={k0?.reference_date ?? ''} max={10} unit="%" />
        <KpiCard label="미 10년 국채" value={f0?.fred_treasury_10y ?? null} prev={f1?.fred_treasury_10y ?? null} date={f0?.reference_date ?? ''} max={8} unit="%" />
      </div>

      {/* 파이프라인 + GPR 추이 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">뉴스 파이프라인 현황</p>
          <div className="flex items-center gap-6">
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie data={pipeData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" paddingAngle={2}>
                  {pipeData.map(entry => (
                    <Cell key={entry.name} fill={PIPE_COLORS[entry.name] ?? '#E5E7EB'} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {pipeData.map(({ name, value }) => (
                <div key={name} className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: PIPE_COLORS[name] ?? '#E5E7EB' }} />
                  <span className="text-xs text-gray-600 w-16">{name}</span>
                  <span className="font-mono text-xs font-medium tabular-nums text-gray-900">{value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">GPR 지수 30일 추이</p>
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={gprTrend ?? []}>
              <XAxis dataKey="reference_date" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} width={35} />
              <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} />
              <Line type="monotone" dataKey="ai_gpr_index" stroke={COLORS.primary} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 카테고리별 인과관계 + 최신 뉴스 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">카테고리별 인과관계</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart layout="vertical" data={causalGrouped} margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F3F4F6" />
              <XAxis type="number" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <YAxis type="category" dataKey="category" tickFormatter={formatCategory} tick={{ fontSize: 10 }} width={80} />
              <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} />
              <Bar dataKey="up"      stackId="a" fill={COLORS.up}      radius={[0,3,3,0]} />
              <Bar dataKey="down"    stackId="a" fill={COLORS.down}    />
              <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">최신 분석 뉴스</p>
          <ul className="space-y-3">
            {(news ?? []).map((item: Record<string, unknown>, i: number) => {
              const chains = item.causal_chains as { direction?: string }[] ?? []
              const dir = chains[0]?.direction ?? 'neutral'
              const dirStyle = DIRECTION_MAP[dir]
              return (
                <li key={item.id as string} className="animate-fade-in-up border-b border-gray-50 pb-3 last:border-0 last:pb-0" style={{ animationDelay: `${i * 60}ms` }}>
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5 text-xs font-bold" style={{ color: dirStyle?.color }}>{dirStyle?.label.split(' ')[0]}</span>
                    <p className="flex-1 text-xs font-medium text-gray-800 line-clamp-2">{item.summary as string}</p>
                  </div>
                  <div className="flex items-center justify-between mt-1 pl-4">
                    <span className="font-mono text-[10px] text-gray-400">{formatDate((item.created_at as string) ?? '')}</span>
                    <ReliabilityBar value={item.reliability as number} />
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
