import { cn } from '../../lib/helpers'

const STATUS_STYLES: Record<string, string> = {
  processed: 'bg-green-50 text-green-700',
  skipped:   'bg-gray-100 text-gray-500',
  pending:   'bg-yellow-50 text-yellow-700',
  failed:    'bg-red-50 text-red-600',
}

export function StatusBadge({ status }: { status: string | null }) {
  const s = status ?? 'pending'
  return (
    <span className={cn('inline-flex items-center rounded px-2 py-0.5 text-xs font-medium font-mono', STATUS_STYLES[s] ?? 'bg-gray-100 text-gray-500')}>
      {s}
    </span>
  )
}

export function DirectionBadge({ direction }: { direction: string }) {
  const styles: Record<string, string> = {
    up:      'text-up bg-[#FCEBEB]',
    down:    'text-down bg-[#EAF3DE]',
    neutral: 'text-gray-500 bg-gray-100',
  }
  const labels: Record<string, string> = { up: '▲ 상승', down: '▼ 하락', neutral: '─ 중립' }
  return (
    <span className={cn('inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold', styles[direction] ?? 'bg-gray-100')}>
      {labels[direction] ?? direction}
    </span>
  )
}

export function ReliabilityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? '#D85A30' : pct >= 50 ? '#EF9F27' : '#B4B2A9'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-gray-200 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="font-mono text-xs text-gray-500">{pct}%</span>
    </div>
  )
}

export function MagnitudeDots({ magnitude }: { magnitude: string }) {
  const dotColors: Record<string, string[]> = {
    high:   ['#D85A30', '#D85A30', '#D85A30'],
    medium: ['#EF9F27', '#EF9F27', '#E5E7EB'],
    low:    ['#E5E7EB', '#E5E7EB', '#E5E7EB'],
  }
  const dots = dotColors[magnitude] ?? dotColors.low
  return (
    <span className="flex gap-1">
      {dots.map((c, i) => <span key={i} className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: c }} />)}
    </span>
  )
}
