export const CATEGORY_MAP: Record<string, string> = {
  fuel:        '연료 · 에너지',
  travel:      '교통 · 여행',
  utility:     '전기 · 가스 · 수도',
  dining:      '식음료',
  neutral:     '기타',
  oil:         '원유 · 유가',
  gas:         '천연가스',
  energy:      '에너지',
  food:        '식료품',
  wheat:       '곡물 · 농산물',
  commodity:   '원자재 · 잡화',
  price:       '물가 · 가격',
  cost:        '생활비 · 가계',
  inflation:   '인플레이션',
  shipping:    '물류 · 운송',
}

export const DIRECTION_MAP: Record<string, { label: string; color: string }> = {
  up:      { label: '▲ 상승', color: '#D85A30' },
  down:    { label: '▼ 하락', color: '#1D9E75' },
  neutral: { label: '─ 중립', color: '#111827' },
}

export const MAGNITUDE_MAP: Record<string, { label: string; dots: string[] }> = {
  high:   { label: '강함', dots: ['#D85A30', '#D85A30', '#D85A30'] },
  medium: { label: '보통', dots: ['#EF9F27', '#EF9F27', '#E5E7EB'] },
  low:    { label: '약함', dots: ['#E5E7EB', '#E5E7EB', '#E5E7EB'] },
}

export function formatCategory(code: string): string {
  return CATEGORY_MAP[code] ?? code ?? '기타'
}

export function getReliabilityStyle(r: number): { bg: string; color: string } | null {
  if (r >= 0.8) return { bg: '#FCEBEB', color: '#791F1F' }
  if (r >= 0.5) return { bg: '#FAEEDA', color: '#633806' }
  if (r >= 0.3) return { bg: '#F1EFE8', color: '#5F5E5A' }
  return null
}
