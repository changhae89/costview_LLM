import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { indicatorApi } from '../lib/api'
import { formatNumber } from '../lib/helpers'
import { COLORS } from '../constants/colors'

type Period = '1M' | '3M' | '6M' | '1Y' | 'ALL'

const PERIOD_DAYS: Record<Period, number | undefined> = {
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
  'ALL': undefined,
}

function PeriodSelector({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  return (
    <div className="flex gap-1">
      {(['1M', '3M', '6M', '1Y', 'ALL'] as Period[]).map(p => (
        <button key={p} onClick={() => onChange(p)}
          className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${value === p ? 'bg-primary text-white' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'}`}>
          {p}
        </button>
      ))}
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-white p-5 border border-gray-100">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">{title}</p>
      {children}
    </div>
  )
}

function GprTab({ period }: { period: Period }) {
  const days = PERIOD_DAYS[period]
  const { data, isLoading } = useQuery({
    queryKey: ['indicator', 'gpr', period],
    queryFn: () => indicatorApi.series('gpr', days),
  })

  return (
    <ChartCard title="글로벌 위기 지수 (GPR)">
      {isLoading ? <div className="h-48 flex items-center justify-center text-sm text-gray-400">로딩 중...</div> : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data ?? []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="reference_date" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} width={40} />
            <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="ai_gpr_index" name="AI GPR" stroke={COLORS.primary} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="gpr_original" name="GPR" stroke={COLORS.neutral} strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}

function EcosTab({ period }: { period: Period }) {
  const days = PERIOD_DAYS[period]
  const { data, isLoading } = useQuery({
    queryKey: ['indicator', 'ecos', period],
    queryFn: () => indicatorApi.series('ecos', days),
  })

  return (
    <ChartCard title="원화 환율 (ECOS)">
      {isLoading ? <div className="h-48 flex items-center justify-center text-sm text-gray-400">로딩 중...</div> : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data ?? []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="reference_date" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} width={50} />
            <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} formatter={(v: number) => formatNumber(v)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="krw_usd_rate" name="KRW/USD" stroke="#0D9488" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}

function FredTab({ period }: { period: Period }) {
  const days = PERIOD_DAYS[period]
  const { data, isLoading } = useQuery({
    queryKey: ['indicator', 'fred', period],
    queryFn: () => indicatorApi.series('fred', days),
  })

  const charts = [
    { title: '원유 가격 (USD)', keys: [{ key: 'fred_wti', name: 'WTI', color: COLORS.primary }, { key: 'fred_brent', name: 'Brent', color: COLORS.up }] },
    { title: '미국 국채 금리 (%)', keys: [{ key: 'fred_treasury_10y', name: '10Y', color: COLORS.primary }, { key: 'fred_treasury_2y', name: '2Y', color: '#F59E0B' }] },
    { title: '천연가스 (USD)', keys: [{ key: 'fred_natural_gas', name: 'Natural Gas', color: '#6366F1' }] },
    { title: '달러 인덱스 (DXY)', keys: [{ key: 'fred_usd_index', name: 'DXY', color: '#EC4899' }] },
  ]

  return (
    <div className="grid grid-cols-2 gap-4">
      {charts.map(({ title, keys }) => (
        <ChartCard key={title} title={title}>
          {isLoading ? <div className="h-36 flex items-center justify-center text-sm text-gray-400">로딩 중...</div> : (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={data ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="reference_date" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickFormatter={v => v.slice(5)} />
                <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} width={40} />
                <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} />
                {keys.map(({ key, name, color }) => (
                  <Line key={key} type="monotone" dataKey={key} name={name} stroke={color} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      ))}
    </div>
  )
}

function KosisTab({ period }: { period: Period }) {
  const days = PERIOD_DAYS[period]
  const { data, isLoading } = useQuery({
    queryKey: ['indicator', 'kosis', period],
    queryFn: () => indicatorApi.series('kosis', days),
  })

  const keys = [
    { key: 'cpi_total', name: '종합', color: COLORS.primary },
    { key: 'core_cpi', name: '근원', color: '#F59E0B' },
    { key: 'cpi_petroleum', name: '석유류', color: COLORS.down },
    { key: 'cpi_agro', name: '농축수산물', color: '#6366F1' },
  ]

  return (
    <ChartCard title="한국 소비자물가지수 (KOSIS, 월별)">
      {isLoading ? <div className="h-48 flex items-center justify-center text-sm text-gray-400">로딩 중...</div> : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data ?? []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="reference_date" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickFormatter={v => v.slice(0, 7)} />
            <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} width={40} unit="%" />
            <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'DM Mono' }} formatter={(v: number) => `${v}%`} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {keys.map(({ key, name, color }) => (
              <Line key={key} type="monotone" dataKey={key} name={name} stroke={color} strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}

type Tab = 'gpr' | 'ecos' | 'fred' | 'kosis'
const TABS: { key: Tab; label: string }[] = [
  { key: 'gpr', label: 'GPR 위기지수' },
  { key: 'ecos', label: '원화 환율' },
  { key: 'fred', label: 'FRED 원자재/금리' },
  { key: 'kosis', label: '한국 CPI' },
]

export function IndicatorPage() {
  const [tab, setTab] = useState<Tab>('gpr')
  const [period, setPeriod] = useState<Period>('3M')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">경제 지표</h1>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {period === 'ALL' && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-2.5 text-xs text-amber-700">
          전체 기간 조회는 데이터가 많아 로딩이 느릴 수 있습니다.
        </div>
      )}

      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t.key ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'gpr' && <GprTab period={period} />}
      {tab === 'ecos' && <EcosTab period={period} />}
      {tab === 'fred' && <FredTab period={period} />}
      {tab === 'kosis' && <KosisTab period={period} />}
    </div>
  )
}
