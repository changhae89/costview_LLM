import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Lightbulb } from 'lucide-react'
import { briefingApi } from '../lib/api'
import { formatDate } from '../lib/helpers'
import { Loading, EmptyState } from '../components/ui/Loading'

type BriefingItem = {
  category_ko: string
  direction: 'up' | 'down' | 'neutral'
  summary: string
  reason: string
}

type Briefing = {
  id: string
  briefing_date: string
  headline: string
  overview: string
  items: BriefingItem[]
  overall_risk: 'low' | 'medium' | 'high'
  consumer_tip: string | null
  source_count: number
  created_at: string
}

const RISK_CONFIG = {
  low:    { label: '안정',     bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-200' },
  medium: { label: '주의',     bg: 'bg-amber-50',  text: 'text-amber-700',  border: 'border-amber-200' },
  high:   { label: '위험',     bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-200' },
}

const DIRECTION_CONFIG = {
  up:      { Icon: TrendingUp,   color: 'text-red-500',   bg: 'bg-red-50',   label: '상승' },
  down:    { Icon: TrendingDown, color: 'text-green-500', bg: 'bg-green-50', label: '하락' },
  neutral: { Icon: Minus,        color: 'text-gray-400',  bg: 'bg-gray-50',  label: '변동없음' },
}

function RiskBadge({ risk }: { risk: 'low' | 'medium' | 'high' }) {
  const cfg = RISK_CONFIG[risk] ?? RISK_CONFIG.medium
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-semibold ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      <AlertTriangle size={11} />
      물가 부담 {cfg.label}
    </span>
  )
}

function DirectionItem({ item }: { item: BriefingItem }) {
  const cfg = DIRECTION_CONFIG[item.direction] ?? DIRECTION_CONFIG.neutral
  const { Icon } = cfg
  return (
    <div className={`flex items-start gap-3 rounded-lg border border-gray-100 p-4 ${cfg.bg}`}>
      <div className={`mt-0.5 flex-shrink-0 ${cfg.color}`}>
        <Icon size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-gray-500">{item.category_ko}</span>
          <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
        </div>
        <p className="text-sm font-semibold text-gray-800 mb-1">{item.summary}</p>
        <p className="text-xs text-gray-500 leading-relaxed">{item.reason}</p>
      </div>
    </div>
  )
}

function EmptyBriefing() {
  return (
    <EmptyState
      message="오늘 브리핑이 아직 준비되지 않았어요"
      sub="매일 오전 브리핑이 자동으로 생성됩니다."
    />
  )
}

export function BriefingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['briefing', 'today'],
    queryFn: briefingApi.today,
  })

  const briefing = data as Briefing | null

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-5xl px-4 py-7 sm:px-6 lg:px-8">
        <div className="space-y-4">
          <div className="flex items-end justify-between gap-3 rounded-lg border border-gray-100 bg-white px-5 py-4">
            <div className="space-y-1">
              <h1 className="text-xl font-bold text-gray-900">오늘의 물가 브리핑</h1>
              <p className="text-xs text-gray-500">AI가 오늘 뉴스를 분석해 장바구니에 미칠 영향을 알려드립니다.</p>
            </div>
            {briefing && (
              <span className="whitespace-nowrap rounded-md bg-gray-50 px-2.5 py-1 font-mono text-xs text-gray-500">
                {briefing.briefing_date}
              </span>
            )}
          </div>

          {isLoading ? (
            <Loading className="py-16" />
          ) : !briefing ? (
            <EmptyBriefing />
          ) : (
            <>
              <div className="rounded-lg bg-white border border-gray-100 shadow-sm p-5 space-y-3.5 animate-fade-in-up">
                <div className="flex items-center justify-between">
                  <RiskBadge risk={briefing.overall_risk} />
                  <span className="text-xs text-gray-400">분석 뉴스 {briefing.source_count}건</span>
                </div>
                <h2 className="text-lg font-bold text-gray-900 leading-snug">{briefing.headline}</h2>
                <p className="text-sm text-gray-600 leading-relaxed">{briefing.overview}</p>
              </div>

              {briefing.items.length > 0 && (
                <div className="rounded-lg bg-white border border-gray-100 shadow-sm p-5 animate-fade-in-up [animation-delay:80ms]">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">품목별 영향</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {briefing.items.map((item, i) => (
                      <DirectionItem key={`${item.category_ko}-${i}`} item={item} />
                    ))}
                  </div>
                </div>
              )}

              {briefing.consumer_tip && (
                <div className="rounded-lg bg-white border border-gray-100 shadow-sm p-5 animate-fade-in-up [animation-delay:160ms]">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">오늘의 생활 팁</p>
                  <div className="flex items-start gap-3 rounded-lg bg-surface border border-primary-accent p-3.5">
                    <Lightbulb size={16} className="mt-0.5 flex-shrink-0 text-primary" />
                    <div>
                      <p className="text-sm text-gray-700">{briefing.consumer_tip}</p>
                    </div>
                  </div>
                </div>
              )}

              <p className="text-center text-[11px] text-gray-400 animate-fade-in-up [animation-delay:240ms]">
                {formatDate(briefing.created_at)} 기준 · AI 분석 결과이며 실제 가격과 다를 수 있습니다
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
