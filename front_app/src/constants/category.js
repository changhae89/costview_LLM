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
  up:      { label: '▲ 상승', color: '#D85A30', dotColor: '#D85A30' },
  down:    { label: '▼ 하락', color: '#1D9E75', dotColor: '#1D9E75' },
  neutral: { label: '─ 중립', color: '#111827', dotColor: '#111827' },
};

export const MAGNITUDE_MAP = {
  high:   { label: '강함',  dots: ['#D85A30', '#D85A30', '#D85A30'] },
  medium: { label: '보통',  dots: ['#EF9F27', '#EF9F27', '#E5E7EB'] },
  low:    { label: '약함',  dots: ['#E5E7EB', '#E5E7EB', '#E5E7EB'] },
};

export function getReliabilityBadge(r) {
  if (r >= 0.8) return { label: `${Math.round(r * 100)}%`, bg: '#FCEBEB', color: '#791F1F' };
  if (r >= 0.5) return { label: `${Math.round(r * 100)}%`, bg: '#FAEEDA', color: '#633806' };
  if (r >= 0.3) return { label: `${Math.round(r * 100)}%`, bg: '#F1EFE8', color: '#5F5E5A' };
  return null; // 0.3 미만 비표시
}

/** DB에 없는 새 코드가 들어와도 영문값 직노웉을 막아주는 포맷터 */
export function formatCategory(code) {
  return CATEGORY_MAP[code] ?? code ?? '기타';
}
