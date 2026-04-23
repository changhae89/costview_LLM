import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Lightbulb, RefreshCw } from 'lucide-react'
import { briefingApi } from '../lib/api'
import { formatDate } from '../lib/helpers'

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
    <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      <AlertTriangle size={11} />
      물가 부담 {cfg.label}
    </span>
  )
}

function DirectionItem({ item }: { item: BriefingItem }) {
  const cfg = DIRECTION_CONFIG[item.direction] ?? DIRECTION_CONFIG.neutral
  const { Icon } = cfg
  return (
    <div className={`flex items-start gap-3 rounded-xl p-4 ${cfg.bg}`}>
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
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-surface">
        <RefreshCw size={24} className="text-primary" />
      </div>
      <p className="text-base font-semibold text-gray-600">오늘 브리핑이 아직 준비되지 않았어요</p>
      <p className="mt-2 text-sm text-gray-400">매일 오전 브리핑이 자동으로 생성됩니다.</p>
    </div>
  )
}

export function BriefingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['briefing', 'today'],
    queryFn: briefingApi.today,
  })

  const briefing = data as Briefing | null

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">오늘의 물가 브리핑</h1>
          <p className="mt-1 text-xs text-gray-500">AI가 오늘 뉴스를 분석해 장바구니에 미칠 영향을 알려드립니다.</p>
        </div>
        {briefing && (
          <span className="font-mono text-xs text-gray-400">{briefing.briefing_date}</span>
        )}
      </div>

      {isLoading ? (
        <div className="py-20 flex items-center justify-center gap-2 text-sm text-gray-400">
          <div className="spinner" /> 브리핑 불러오는 중...
        </div>
      ) : !briefing ? (
        <EmptyBriefing />
      ) : (
        <>
          <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-6 space-y-3 animate-fade-in-up">
            <div className="flex items-center justify-between">
              <RiskBadge risk={briefing.overall_risk} />
              <span className="text-xs text-gray-400">분석 뉴스 {briefing.source_count}건</span>
            </div>
            <h2 className="text-lg font-bold text-gray-900 leading-snug">{briefing.headline}</h2>
            <p className="text-sm text-gray-600 leading-relaxed">{briefing.overview}</p>
          </div>

          {briefing.items.length > 0 && (
            <div className="space-y-2 animate-fade-in-up [animation-delay:80ms]">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">품목별 영향</p>
              {briefing.items.map((item, i) => (
                <DirectionItem key={`${item.category_ko}-${i}`} item={item} />
              ))}
            </div>
          )}

          {briefing.consumer_tip && (
            <div className="flex items-start gap-3 rounded-xl bg-surface border border-primary-accent p-4 animate-fade-in-up [animation-delay:160ms]">
              <Lightbulb size={16} className="mt-0.5 flex-shrink-0 text-primary" />
              <div>
                <p className="text-xs font-semibold text-primary mb-1">오늘의 생활 팁</p>
                <p className="text-sm text-gray-700">{briefing.consumer_tip}</p>
              </div>
            </div>
          )}

          <p className="text-center text-[11px] text-gray-300 animate-fade-in-up [animation-delay:240ms]">
            {formatDate(briefing.created_at)} 기준 · AI 분석 결과이며 실제 가격과 다를 수 있습니다
          </p>
        </>
      )}
    </div>
  )
}
