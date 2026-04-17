// constants/category.js — 설계서 1. 앱 공통 사항

export const CATEGORY_MAP = {
  fuel:    '연료 · 에너지',
  travel:  '교통 · 여행',
  utility: '전기 · 가스 · 수도',
  dining:  '식음료',
  neutral: '기타',
};

export const DIRECTION_MAP = {
  up:      { label: '▲ 상승', color: '#D85A30', dotColor: '#D85A30' },
  down:    { label: '▼ 하락', color: '#1D9E75', dotColor: '#1D9E75' },
  neutral: { label: '─ 중립', color: '#888780', dotColor: '#B4B2A9' },
};

export const MAGNITUDE_MAP = {
  high:   { label: '강함',  dots: ['#D85A30', '#D85A30', '#D85A30'] },
  medium: { label: '보통',  dots: ['#EF9F27', '#EF9F27', '#E5E7EB'] },
  low:    { label: '약함',  dots: ['#E5E7EB', '#E5E7EB', '#E5E7EB'] },
};

export function getReliabilityBadge(r) {
  if (r >= 0.8) return { label: `高 ${Math.round(r * 100)}%`, bg: '#FCEBEB', color: '#791F1F' };
  if (r >= 0.5) return { label: `中 ${Math.round(r * 100)}%`, bg: '#FAEEDA', color: '#633806' };
  if (r >= 0.3) return { label: `低 ${Math.round(r * 100)}%`, bg: '#F1EFE8', color: '#5F5E5A' };
  return null; // 0.3 미만 비표시
}
