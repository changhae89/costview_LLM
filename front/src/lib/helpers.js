// lib/helpers.js — 설계서 8. 데이터 처리 규칙

/** monthly_impact 이상값 처리 */
export function formatMonthlyImpact(val) {
  if (val === null || val === undefined) return '-';
  if (val === 0) return '단기';
  if (val > 999999) return '장기';
  return `${val}개월`;
}

/** 지수 표시 (소수점 1자리) */
export function formatIndex(val) {
  if (val === null || val === undefined) return '-';
  return Number(val).toFixed(1);
}

/** 석유 공급 차질 지수 (차트 표시 시 ÷10) */
export function normalizeOilDisruption(val) {
  return parseFloat((val / 10).toFixed(1));
}

/** reference_date가 text 타입 ('2026-03-31') */
export function formatRefDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
}

/** 전일 대비 변동폭 문자열 */
export function formatChange(change) {
  if (change === null || change === undefined) return '-';
  const n = Number(change);
  if (n > 0) return `▲+${n.toFixed(1)}`;
  if (n < 0) return `▼${n.toFixed(1)}`;
  return '─ 0.0';
}

/** 숫자 천 단위 콤마 */
export function formatNumber(val) {
  if (val === null || val === undefined) return '-';
  return Number(val).toLocaleString('ko-KR', { maximumFractionDigits: 1 });
}

/** 차트 통계 계산 */
export function calcStats(data, key) {
  if (!data || data.length < 2) return null;
  const vals = data.map(d => Number(d[key]) || 0);
  const last = vals[vals.length - 1];
  const prev = vals[vals.length - 2];
  const change = parseFloat((last - prev).toFixed(1));
  const max = Math.max(...vals);
  const min = Math.min(...vals);
  const maxIdx = vals.indexOf(max);
  const minIdx = vals.indexOf(min);
  const maxDate = data[maxIdx]?.reference_date;
  const minDate = data[minIdx]?.reference_date;
  return { last, change, max, min, maxDate, minDate };
}
