import { useEffect, useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { causalApi } from '../lib/api'
import { DirectionBadge, MagnitudeDots, ReliabilityBar } from '../components/ui/Badge'
import { Pagination } from '../components/ui/Pagination'
import { Drawer } from '../components/ui/Drawer'
import { formatCategory } from '../constants/category'
import { formatPct, formatDate } from '../lib/helpers'
import { COLORS } from '../constants/colors'
import { Loading, EmptyState } from '../components/ui/Loading'

const PAGE_SIZE = 50
const CATS = ['fuel','food','energy','gas','shipping','price','commodity','cost','oil','inflation']
const DIRS = ['up','down','neutral']
const MAGS = ['high','medium','low']
const MONTHS = [1,2,3,6]

type Filters = { category: string; direction: string; magnitude: string; transmissionMonths: number }

export function CausalPage() {
  const [page, setPage]       = useState(0)
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null)
  const [filters, setFilters] = useState<Filters>({ category: '', direction: '', magnitude: '', transmissionMonths: 0 })

  useEffect(() => { setPage(0) }, [filters])

  const set = (k: keyof Filters, v: string | number) =>
    setFilters(f => ({ ...f, [k]: f[k] === v ? (typeof v === 'number' ? 0 : '') : v }))

  const { data, isLoading } = useQuery({
    queryKey: ['causal', page, filters],
    queryFn: () => causalApi.list(page, PAGE_SIZE, {
      category: filters.category || undefined,
      direction: filters.direction || undefined,
      magnitude: filters.magnitude || undefined,
      transmissionMonths: filters.transmissionMonths || undefined,
    }),
  })
  const { data: stats } = useQuery({ queryKey: ['causalStats'], queryFn: causalApi.stats })
  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE)

  const catChart = useMemo(() => {
    const map: Record<string, { category: string; up: number; down: number; neutral: number }> = {}
    ;(stats ?? []).forEach((r: Record<string, unknown>) => {
      const cat = r.category as string
      if (!map[cat]) map[cat] = { category: cat, up: 0, down: 0, neutral: 0 }
      const d = (r.direction as string) ?? 'neutral'
      if (d in map[cat]) map[cat][d as 'up'|'down'|'neutral']++
    })
    return Object.values(map).sort((a,b) => (b.up+b.down)-(a.up+a.down))
  }, [stats])

  const shockHist = useMemo(() => {
    const bins = [
      { label: '<-50',    min: -Infinity, max: -50 },
      { label: '-50~0',   min: -50,       max: 0   },
      { label: '0~10',    min: 0,         max: 10  },
      { label: '10~30',   min: 10,        max: 30  },
      { label: '30~100',  min: 30,        max: 100 },
      { label: '>100',    min: 100,       max: Infinity },
    ]
    const counts = bins.map(b => ({ ...b, count: 0 }))
    ;(stats ?? []).forEach((r: Record<string, unknown>) => {
      const v = r.raw_shock_percent as number
      if (v == null || v === 0) return
      const bin = counts.find(b => v >= b.min && v < b.max)
      if (bin) bin.count++
    })
    return counts
  }, [stats])

  const monthDist = useMemo(() => {
    const map: Record<number, number> = {}
    ;(stats ?? []).forEach((r: Record<string, unknown>) => {
      const m = r.transmission_time_months as number
      if (m) map[m] = (map[m] ?? 0) + 1
    })
    return Object.entries(map).map(([m, count]) => ({ month: `${m}개월`, count })).sort((a,b)=>parseInt(a.month)-parseInt(b.month))
  }, [stats])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">물가 영향 분석</h1>

      {/* 필터 */}
      <div className="flex flex-wrap gap-2 rounded-xl bg-white p-3 border border-gray-100 shadow-sm animate-fade-in-up [animation-delay:80ms]">
        {CATS.map(c => (
          <button key={c} onClick={() => set('category', c)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${filters.category === c ? 'bg-primary text-white border-primary' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
            {formatCategory(c)}
          </button>
        ))}
        <div className="w-px bg-gray-200 mx-1" />
        {DIRS.map(d => (
          <button key={d} onClick={() => set('direction', d)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${filters.direction === d ? 'bg-primary text-white border-primary' : 'border-gray-200 text-gray-500'}`}>
            {d === 'up' ? '▲ 상승' : d === 'down' ? '▼ 하락' : '─ 중립'}
          </button>
        ))}
        <div className="w-px bg-gray-200 mx-1" />
        {MAGS.map(m => (
          <button key={m} onClick={() => set('magnitude', m)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${filters.magnitude === m ? 'bg-primary text-white border-primary' : 'border-gray-200 text-gray-500'}`}>
            {m === 'high' ? '강함' : m === 'medium' ? '보통' : '약함'}
          </button>
        ))}
        <div className="w-px bg-gray-200 mx-1" />
        {MONTHS.map(m => (
          <button key={m} onClick={() => set('transmissionMonths', m)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${filters.transmissionMonths === m ? 'bg-primary text-white border-primary' : 'border-gray-200 text-gray-500'}`}>
            {m}개월
          </button>
        ))}
      </div>

      {/* 차트 3개 */}
      <div className="grid grid-cols-3 gap-4 animate-fade-in-up [animation-delay:160ms]">
        <div className="rounded-lg bg-white p-4 border border-gray-100 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">품목별 방향</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart layout="vertical" data={catChart} margin={{ left: 10 }}>
              <XAxis type="number" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <YAxis type="category" dataKey="category" tickFormatter={formatCategory} tick={{ fontSize: 9 }} width={72} />
              <Tooltip contentStyle={{ fontSize: 10 }} />
              <Bar dataKey="up"      stackId="a" fill={COLORS.up}      />
              <Bar dataKey="down"    stackId="a" fill={COLORS.down}    />
              <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} radius={[0,3,3,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg bg-white p-4 border border-gray-100 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">가격 충격 분포</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={shockHist}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F3F4F6" />
              <XAxis dataKey="label" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <Tooltip contentStyle={{ fontSize: 10 }} />
              <Bar dataKey="count" fill={COLORS.primary} radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg bg-white p-4 border border-gray-100 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">영향 전달 기간</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={monthDist}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F3F4F6" />
              <XAxis dataKey="month" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <YAxis tick={{ fontSize: 9, fontFamily: 'DM Mono' }} />
              <Tooltip contentStyle={{ fontSize: 10 }} />
              <Bar dataKey="count" fill={COLORS.series3} radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 테이블 */}
      <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden animate-fade-in-up [animation-delay:240ms]">
        <div className="px-4 py-2.5 border-b border-gray-50">
          <span className="font-mono text-xs text-gray-400">총 {(data?.total ?? 0).toLocaleString()}건</span>
        </div>
        {isLoading ? <Loading /> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">이벤트</th>
                <th className="px-4 py-2.5 text-left font-medium w-24">카테고리</th>
                <th className="px-4 py-2.5 text-left font-medium w-24">방향</th>
                <th className="px-4 py-2.5 text-left font-medium w-20">강도</th>
                <th className="px-4 py-2.5 text-right font-medium w-20">원충격%</th>
                <th className="px-4 py-2.5 text-right font-medium w-20">지갑%</th>
                <th className="px-4 py-2.5 text-center font-medium w-16">전달</th>
                <th className="px-4 py-2.5 text-center font-medium w-14">단계</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">신뢰도</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {!(data?.data ?? []).length && (
                <tr><td colSpan={9}><EmptyState message="인과관계 데이터가 없습니다" sub="필터 조건을 변경해 보세요" /></td></tr>
              )}
              {(data?.data ?? []).map((row: Record<string, unknown>) => {
                const analysis = row.news_analyses as Record<string, unknown>
                return (
                  <tr key={row.id as string} onClick={() => setSelected(row)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-4 py-3 max-w-xs">
                      <p className="text-gray-800 line-clamp-1 text-xs" title={row.event as string}>{row.event as string}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{formatCategory(row.category as string)}</td>
                    <td className="px-4 py-3"><DirectionBadge direction={row.direction as string} /></td>
                    <td className="px-4 py-3"><MagnitudeDots magnitude={row.magnitude as string} /></td>
                    <td className="px-4 py-3 text-right font-mono text-xs" style={{ color: (row.raw_shock_percent as number) >= 0 ? COLORS.up : COLORS.down }}>
                      {formatPct(row.raw_shock_percent as number)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs" style={{ color: (row.wallet_hit_percent as number) >= 0 ? COLORS.up : COLORS.down }}>
                      {formatPct(row.wallet_hit_percent as number)}
                    </td>
                    <td className="px-4 py-3 text-center font-mono text-xs text-gray-500">{row.transmission_time_months as number}개월</td>
                    <td className="px-4 py-3 text-center font-mono text-xs text-gray-500">
                      {Array.isArray(row.logic_steps) ? row.logic_steps.length : 0}단계
                    </td>
                    <td className="px-4 py-3">
                      {analysis && <ReliabilityBar value={analysis.reliability as number} />}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
        <div className="px-4 pb-3">
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </div>
      </div>

      {/* 상세 Drawer */}
      <Drawer open={!!selected} onClose={() => setSelected(null)} title="영향 분석 상세">
        {selected && (
          <div className="space-y-5 text-sm">
            <div className="flex flex-wrap gap-2">
              <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded">{formatCategory(selected.category as string)}</span>
              <DirectionBadge direction={selected.direction as string} />
              <MagnitudeDots magnitude={selected.magnitude as string} />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-400 mb-1">이벤트</p>
              <p className="font-semibold text-gray-900">{selected.event as string}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-400 mb-1">메커니즘</p>
              <p className="text-xs text-gray-600 leading-relaxed">{selected.mechanism as string}</p>
            </div>
            {Array.isArray(selected.logic_steps) && (
              <div>
                <p className="text-xs font-medium text-gray-400 mb-2">인과 단계</p>
                <div className="flex flex-wrap items-center gap-1">
                  {(selected.logic_steps as { step: number; description: string }[]).map((s, i) => (
                    <span key={i} className="flex items-center gap-1">
                      <span className="text-xs bg-surface px-2 py-1 rounded text-gray-700">{s.description}</span>
                      {i < (selected.logic_steps as unknown[]).length - 1 && <span className="text-gray-300 text-xs">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-gray-400 mb-1">충격 요인</p>
                <div className="flex flex-wrap gap-1">
                  {((selected.raw_shock_factors as string[]) ?? []).map((f, i) => (
                    <span key={i} className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded">{f}</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">지갑 영향 요인</p>
                <div className="flex flex-wrap gap-1">
                  {((selected.wallet_hit_factors as string[]) ?? []).map((f, i) => (
                    <span key={i} className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded">{f}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 font-mono text-xs bg-surface rounded-lg p-3">
              <div><span className="text-gray-400">원충격</span><br /><span className="font-medium" style={{ color: (selected.raw_shock_percent as number) >= 0 ? COLORS.up : COLORS.down }}>{formatPct(selected.raw_shock_percent as number)}</span></div>
              <div><span className="text-gray-400">지갑영향</span><br /><span className="font-medium" style={{ color: (selected.wallet_hit_percent as number) >= 0 ? COLORS.up : COLORS.down }}>{formatPct(selected.wallet_hit_percent as number)}</span></div>
              <div><span className="text-gray-400">전달기간</span><br />{selected.transmission_time_months as number}개월</div>
              <div><span className="text-gray-400">전달 이유</span><br /><span className="text-gray-600">{selected.transmission_rationale as string}</span></div>
            </div>
            {!!selected.news_analyses && (
              <div>
                <p className="text-xs font-medium text-gray-400 mb-2">연결된 뉴스 분석</p>
                <div className="rounded-lg bg-surface p-3 space-y-2">
                  <p className="text-xs text-gray-700">{(selected.news_analyses as Record<string,unknown>).summary as string}</p>
                  <div className="flex items-center justify-between">
                    <ReliabilityBar value={(selected.news_analyses as Record<string,unknown>).reliability as number} />
                    <span className="font-mono text-[10px] text-gray-400">{formatDate((selected.news_analyses as Record<string,unknown>).created_at as string)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  )
}
