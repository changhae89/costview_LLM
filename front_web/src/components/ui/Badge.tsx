import { cn } from '../../lib/helpers'
import { COLORS } from '../../constants/colors'

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
  const config: Record<string, { bg: string; color: string; label: string }> = {
    up:      { bg: COLORS.tagUpBg,   color: COLORS.tagUpText,   label: '▲ 상승' },
    down:    { bg: COLORS.tagDownBg, color: COLORS.tagDownText, label: '▼ 하락' },
    neutral: { bg: '#F3F4F6',        color: COLORS.textMuted,   label: '─ 중립' },
  }
  const c = config[direction] ?? config.neutral
  return (
    <span
      className="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: c.bg, color: c.color }}
    >
      {c.label}
    </span>
  )
}

export function ReliabilityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? COLORS.primary : pct >= 50 ? COLORS.warning : COLORS.neutral
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
    high:   [COLORS.dotHigh, COLORS.dotHigh, COLORS.dotHigh],
    medium: [COLORS.dotMed,  COLORS.dotMed,  COLORS.dotLow],
    low:    [COLORS.dotLow,  COLORS.dotLow,  COLORS.dotLow],
  }
  const dots = dotColors[magnitude] ?? dotColors.low
  return (
    <span className="flex gap-1">
      {dots.map((c, i) => <span key={i} className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: c }} />)}
    </span>
  )
}
