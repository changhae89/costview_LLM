// constants/category.js — 설계서 1. 앱 공통 사항

export const CATEGORY_MAP = {
  // 현재 DB에 존재하는 코드
  fuel:        '연료 · 에너지',
  travel:      '교통 · 여행',
  utility:     '전기 · 가스 · 수도',
  dining:      '식음료',
  neutral:     '기타',
  // 추가 및 백엔드 연동 키워드
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
  // 추가 카테고리 (DB 확장 대비)
  housing:     '주거 · 부동산',
  healthcare:  '보건 · 의료',
  education:   '교육',
  finance:     '금융',
  agriculture: '농산물',
  industrial:  '산업 · 제조',
  tech:        'IT · 테크',
};

export const DIRECTION_MAP = {
  up:      { label: '▲ 상승', color: '#EF4444', dotColor: '#EF4444' },
  down:    { label: '▼ 하락', color: '#22C55E', dotColor: '#22C55E' },
  neutral: { label: '─ 중립', color: '#9CA3AF', dotColor: '#9CA3AF' },
};

export const MAGNITUDE_MAP = {
  high:   { label: '강함',  dots: ['#EF4444', '#EF4444', '#EF4444'] },
  medium: { label: '보통',  dots: ['#F59E0B', '#F59E0B', '#E5E7EB'] },
  low:    { label: '약함',  dots: ['#E5E7EB', '#E5E7EB', '#E5E7EB'] },
};

export function getReliabilityBadge(r) {
  if (r >= 0.8) return { label: `${Math.round(r * 100)}%`, bg: '#FFF7ED', color: '#EA580C' };
  if (r >= 0.5) return { label: `${Math.round(r * 100)}%`, bg: '#FFFBEB', color: '#92400E' };
  if (r >= 0.3) return { label: `${Math.round(r * 100)}%`, bg: '#F9FAFB', color: '#6B7280' };
  return null; // 0.3 미만 비표시
}

/** DB에 없는 새 코드가 들어와도 영문값 직노웉을 막아주는 포맷터 */
export function formatCategory(code) {
  return CATEGORY_MAP[code] ?? code ?? '기타';
}
