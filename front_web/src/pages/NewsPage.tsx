import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { newsApi } from '../lib/api'
import { StatusBadge, ReliabilityBar } from '../components/ui/Badge'
import { Pagination } from '../components/ui/Pagination'
import { Drawer } from '../components/ui/Drawer'
import { formatDate } from '../lib/helpers'
import { formatCategory } from '../constants/category'
import { COLORS } from '../constants/colors'

const PAGE_SIZE = 50
const STATUSES = ['processed', 'skipped', 'pending', 'failed']

export function NewsPage() {
  const [tab, setTab] = useState<'raw' | 'analyses'>('raw')

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">뉴스 관리</h1>
      <div className="flex gap-1 border-b border-gray-200">
        {(['raw', 'analyses'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t === 'raw' ? '원본 뉴스' : '분석 결과'}
          </button>
        ))}
      </div>
      {tab === 'raw' ? <RawNewsTab /> : <AnalysesTab />}
    </div>
  )
}

function RawNewsTab() {
  const [page, setPage]           = useState(0)
  const [search, setSearch]       = useState('')
  const [statuses, setStatuses]   = useState<string[]>([])
  const [showDeleted, setDeleted] = useState(false)
  const [selected, setSelected]   = useState<Record<string, unknown> | null>(null)

  const filters = { search, status: statuses, showDeleted }
  useEffect(() => { setPage(0) }, [search, statuses, showDeleted])

  const { data, isLoading } = useQuery({
    queryKey: ['rawNews', page, filters],
    queryFn: () => newsApi.raw(page, PAGE_SIZE, filters),
  })
  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE)

  const toggleStatus = (s: string) =>
    setStatuses(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  return (
    <>
      {/* 필터 바 */}
      <div className="flex flex-wrap gap-3 items-center rounded-xl bg-white p-3 border border-gray-100">
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="제목 검색..." className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm w-48 outline-none focus:border-primary" />
        <div className="flex gap-2">
          {STATUSES.map(s => (
            <button key={s} onClick={() => toggleStatus(s)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors font-medium ${statuses.includes(s) ? 'bg-primary text-white border-primary' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
              {s}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer ml-auto">
          <input type="checkbox" checked={showDeleted} onChange={e => setDeleted(e.target.checked)} className="rounded" />
          삭제 항목 포함
        </label>
      </div>

      <div className="rounded-xl bg-white border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-50">
          <span className="font-mono text-xs text-gray-400">총 {(data?.total ?? 0).toLocaleString()}건</span>
        </div>
        {isLoading ? <div className="py-12 text-center text-sm text-gray-400">로딩 중...</div> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">제목</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">상태</th>
                <th className="px-4 py-2.5 text-left font-medium w-32">키워드</th>
                <th className="px-4 py-2.5 text-left font-medium w-24">발행일</th>
                <th className="px-4 py-2.5 text-center font-medium w-16">재시도</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {(data?.data ?? []).map((row: Record<string, unknown>) => (
                <tr key={row.id as string} onClick={() => setSelected(row)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-gray-800 line-clamp-1">{row.title as string}</p>
                      {!!row.news_url && (
                        <a href={row.news_url as string} target="_blank" rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()} className="text-gray-300 hover:text-primary shrink-0">
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {((row.increased_items as string[]) ?? []).map(k => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: COLORS.tagUpBg, color: COLORS.tagUpText }}>▲{formatCategory(k)}</span>
                      ))}
                      {((row.decreased_items as string[]) ?? []).map(k => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: COLORS.tagDownBg, color: COLORS.tagDownText }}>▼{formatCategory(k)}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={row.processing_status as string} /></td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {((row.keyword as string[]) ?? []).slice(0, 3).map(k => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{k}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{formatDate(row.origin_published_at as string)}</td>
                  <td className="px-4 py-3 text-center font-mono text-xs text-gray-400">{row.retry_count as number}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="px-4 pb-3">
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </div>
      </div>

      <Drawer open={!!selected} onClose={() => setSelected(null)} title="뉴스 상세">
        {selected && (
          <div className="space-y-4 text-sm">
            <p className="font-semibold text-gray-900">{selected.title as string}</p>
            <StatusBadge status={selected.processing_status as string} />
            <div className="space-y-1">
              <p className="text-xs font-medium text-gray-500">URL</p>
              <a href={selected.news_url as string} target="_blank" rel="noopener noreferrer" className="text-xs text-primary break-all">{selected.news_url as string}</a>
            </div>
            <div className="grid grid-cols-2 gap-3 font-mono text-xs text-gray-600">
              <div><span className="text-gray-400">발행일</span><br />{formatDate(selected.origin_published_at as string)}</div>
              <div><span className="text-gray-400">재시도</span><br />{selected.retry_count as number}회</div>
            </div>
          </div>
        )}
      </Drawer>
    </>
  )
}

function AnalysesTab() {
  const [page, setPage]       = useState(0)
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['analyses', page],
    queryFn: () => newsApi.analyses(page, PAGE_SIZE),
  })
  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE)

  return (
    <>
      <div className="rounded-xl bg-white border border-gray-100 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-gray-50">
          <span className="font-mono text-xs text-gray-400">총 {(data?.total ?? 0).toLocaleString()}건</span>
        </div>
        {isLoading ? <div className="py-12 text-center text-sm text-gray-400">로딩 중...</div> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">요약</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">신뢰도</th>
                <th className="px-4 py-2.5 text-left font-medium w-20">지평선</th>
                <th className="px-4 py-2.5 text-left font-medium w-20">지리</th>
                <th className="px-4 py-2.5 text-left font-medium w-20">한국 관련</th>
                <th className="px-4 py-2.5 text-left font-medium w-28">분석일</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {(data?.data ?? []).map((row: Record<string, unknown>) => (
                <tr key={row.id as string} onClick={() => setSelected(row)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                  <td className="px-4 py-3 max-w-xs">
                    <p className="font-medium text-gray-800 line-clamp-2">{row.summary as string}</p>
                  </td>
                  <td className="px-4 py-3"><ReliabilityBar value={row.reliability as number} /></td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.time_horizon as string}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.geo_scope as string}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{row.korea_relevance as string}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{formatDate(row.created_at as string)}</td>
                </tr>
              ))}
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
            <p className="font-semibold text-gray-900">{selected.summary as string}</p>
            <ReliabilityBar value={selected.reliability as number} />
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">신뢰도 이유</p>
              <p className="text-xs text-gray-600">{selected.reliability_reason as string ?? '-'}</p>
            </div>
            {Array.isArray(selected.effect_chain) && selected.effect_chain.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">인과 흐름</p>
                <div className="flex flex-wrap items-center gap-1 text-xs">
                  {(selected.effect_chain as string[]).map((s, i) => (
                    <span key={i} className="flex items-center gap-1">
                      <span className="bg-surface px-2 py-1 rounded text-gray-700">{s}</span>
                      {i < (selected.effect_chain as string[]).length - 1 && <span className="text-gray-300">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="grid grid-cols-3 gap-2 font-mono text-xs text-gray-600">
              <div><span className="text-gray-400 block">지평선</span>{selected.time_horizon as string}</div>
              <div><span className="text-gray-400 block">지리</span>{selected.geo_scope as string}</div>
              <div><span className="text-gray-400 block">한국 관련</span>{selected.korea_relevance as string}</div>
            </div>
          </div>
        )}
      </Drawer>
    </>
  )
}
