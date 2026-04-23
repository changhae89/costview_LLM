import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarDays, Filter, Search, ShieldCheck } from 'lucide-react'
import { newsApi } from '../lib/api'
import { ReliabilityBar } from '../components/ui/Badge'
import { Pagination } from '../components/ui/Pagination'
import { Drawer } from '../components/ui/Drawer'
import { Loading, EmptyState } from '../components/ui/Loading'
import { formatDate } from '../lib/helpers'

const PAGE_SIZE = 50
const HORIZONS = ['short', 'medium', 'long']
const GEO_SCOPES = ['korea', 'global', 'asia', 'other']
const KOREA_RELEVANCE = ['direct', 'indirect', 'none']

type AnalysisRow = {
  id: string
  summary: string
  reliability: number
  time_horizon: string | null
  geo_scope: string | null
  korea_relevance: string | null
  created_at: string
  effect_chain?: string[]
  reliability_reason?: string | null
  raw_news_id?: string | null
}

function SelectFilter({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  options: string[]
  placeholder: string
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="h-9 rounded-lg border border-gray-200 bg-white px-3 text-xs text-gray-600 outline-none focus:border-primary"
    >
      <option value="">{placeholder}</option>
      {options.map(option => (
        <option key={option} value={option}>{option}</option>
      ))}
    </select>
  )
}

function Metric({ label, value, icon: Icon }: { label: string; value: string; icon: typeof ShieldCheck }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Icon size={14} />
        <span>{label}</span>
      </div>
      <p className="mt-2 font-mono text-xl font-semibold text-gray-900">{value}</p>
    </div>
  )
}

export function NewsPage() {
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [minReliability, setMinReliability] = useState('')
  const [timeHorizon, setTimeHorizon] = useState('')
  const [geoScope, setGeoScope] = useState('')
  const [koreaRelevance, setKoreaRelevance] = useState('')
  const [selected, setSelected] = useState<AnalysisRow | null>(null)

  const filters = {
    search,
    minReliability: minReliability ? Number(minReliability) : undefined,
    timeHorizon,
    geoScope,
    koreaRelevance,
  }

  useEffect(() => { setPage(0) }, [search, minReliability, timeHorizon, geoScope, koreaRelevance])

  const { data, isLoading } = useQuery({
    queryKey: ['analyses', page, filters],
    queryFn: () => newsApi.analyses(page, PAGE_SIZE, filters),
  })

  const rows = (data?.data ?? []) as AnalysisRow[]
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  const pageStats = useMemo(() => {
    const avg = rows.length
      ? Math.round(rows.reduce((sum, row) => sum + (row.reliability ?? 0), 0) / rows.length * 100)
      : 0
    const direct = rows.filter(row => row.korea_relevance === 'direct').length
    const high = rows.filter(row => row.reliability >= 0.8).length
    return { avg, direct, high }
  }, [rows])

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">뉴스 관리</h1>
          <p className="mt-1 text-xs text-gray-500">분석된 뉴스와 신뢰도, 영향 경로를 관리합니다.</p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 animate-fade-in-up [animation-delay:80ms]">
        <Metric label="분석 뉴스" value={`${total.toLocaleString()}건`} icon={CalendarDays} />
        <Metric label="현재 페이지 평균 신뢰도" value={`${pageStats.avg}%`} icon={ShieldCheck} />
        <Metric label="한국 직접 관련" value={`${pageStats.direct.toLocaleString()}건`} icon={Filter} />
        <Metric label="고신뢰 분석" value={`${pageStats.high.toLocaleString()}건`} icon={ShieldCheck} />
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-white p-3 border border-gray-100 shadow-sm animate-fade-in-up [animation-delay:160ms]">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="요약 검색..."
            className="h-9 w-72 rounded-lg border border-gray-200 pl-9 pr-3 text-sm outline-none focus:border-primary"
          />
        </div>
        <SelectFilter value={minReliability} onChange={setMinReliability} options={['0.8', '0.7', '0.5']} placeholder="신뢰도" />
        <SelectFilter value={timeHorizon} onChange={setTimeHorizon} options={HORIZONS} placeholder="영향 시기" />
        <SelectFilter value={geoScope} onChange={setGeoScope} options={GEO_SCOPES} placeholder="영향 지역" />
        <SelectFilter value={koreaRelevance} onChange={setKoreaRelevance} options={KOREA_RELEVANCE} placeholder="한국 관련도" />
      </div>

      <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden animate-fade-in-up [animation-delay:240ms]">
        <div className="px-4 py-2.5 border-b border-gray-50">
          <span className="font-mono text-xs text-gray-400">총 {total.toLocaleString()}건</span>
        </div>
        {isLoading ? <Loading /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">요약</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">신뢰도</th>
                <th className="px-4 py-2.5 text-left font-medium w-24">영향 시기</th>
                <th className="px-4 py-2.5 text-left font-medium w-24">영향 지역</th>
                <th className="px-4 py-2.5 text-left font-medium w-24">한국 관련도</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">분석일</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {rows.map(row => (
                <tr key={row.id} onClick={() => setSelected(row)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                  <td className="px-4 py-3 max-w-3xl">
                    <p className="font-medium text-gray-800 line-clamp-2">{row.summary}</p>
                  </td>
                  <td className="px-4 py-3"><ReliabilityBar value={row.reliability} /></td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.time_horizon ?? '-'}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.geo_scope ?? '-'}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.korea_relevance ?? '-'}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{formatDate(row.created_at)}</td>
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan={6}><EmptyState message="분석 결과가 없습니다" sub="필터 조건을 변경해 보세요" /></td></tr>
              )}
            </tbody>
          </table>
        )}
        <div className="px-4 pb-3">
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </div>
      </div>

      <Drawer open={!!selected} onClose={() => setSelected(null)} title="분석 상세">
        {selected && (
          <div className="space-y-5 text-sm">
            <p className="font-semibold text-gray-900 leading-relaxed">{selected.summary}</p>
            <ReliabilityBar value={selected.reliability} />
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">신뢰도 근거</p>
              <p className="text-xs text-gray-600 leading-relaxed">{selected.reliability_reason ?? '-'}</p>
            </div>
            {!!selected.effect_chain?.length && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">영향 경로</p>
                <div className="flex flex-wrap items-center gap-1 text-xs">
                  {selected.effect_chain.map((step, i) => (
                    <span key={`${step}-${i}`} className="flex items-center gap-1">
                      <span className="bg-surface px-2 py-1 rounded text-gray-700">{step}</span>
                      {i < selected.effect_chain!.length - 1 && <span className="text-gray-300">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="grid grid-cols-3 gap-2 font-mono text-xs text-gray-600">
              <div><span className="text-gray-400 block">지평선</span>{selected.time_horizon ?? '-'}</div>
              <div><span className="text-gray-400 block">지역</span>{selected.geo_scope ?? '-'}</div>
              <div><span className="text-gray-400 block">한국 관련</span>{selected.korea_relevance ?? '-'}</div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
