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

/** 차트 통계 계산 — null/undefined는 계산에서 제외 (0으로 대체 시 최솟값 왜곡 발생) */
export function calcStats(data, key) {
  if (!data || data.length < 2) return null;

  // null/undefined/NaN 제거 후 실제 데이터만 사용
  const validPairs = data
    .map((d, i) => ({ val: Number(d[key]), i, date: d.reference_date }))
    .filter(({ val }) => !isNaN(val) && val !== null && val !== undefined);

  if (validPairs.length < 2) return null;

  const vals = validPairs.map(p => p.val);
  const last = vals[vals.length - 1];
  const prev = vals[vals.length - 2];
  const change = parseFloat((last - prev).toFixed(1));
  const max = Math.max(...vals);
  const min = Math.min(...vals);
  const maxDate = validPairs[vals.indexOf(max)]?.date;
  const minDate = validPairs[vals.indexOf(min)]?.date;
  return { last, change, max, min, maxDate, minDate };
}

/** 날짜 시간 표시 (2026.04.21 11:44) */
export function formatDateTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${y}.${m}.${dd} ${hh}:${mm}`;
}
