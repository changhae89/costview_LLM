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

/** 리스크 상세 바텀 시트 벤치마크 생성 함수 */
export function getBenchmarkText(key, value) {
  if (value === null || value === undefined) return "수치를 불러올 수 없습니다.";
  const val = Number(value);

  switch (key) {
    case 'ai_gpr':
      if (val >= 310) return `현재 지수(${val.toFixed(1)})는 2022년 3월 우크라이나 침공(약 319) 수준에 근접한 초고위험 수치입니다.`;
      if (val >= 260) return `현재 지수(${val.toFixed(1)})는 2001년 9.11 테러(약 263) 및 1991년 걸프 전쟁(약 260) 수준의 고위험 수치입니다.`;
      if (val >= 240) return `현재 지수(${val.toFixed(1)})는 2003년 이라크 전쟁(약 245) 및 2023년 이스라엘-하마스 전쟁(약 242) 당시와 유사한 수치입니다.`;
      if (val >= 150) return `현재 지수(${val.toFixed(1)})는 평시 평균(약 100)을 상회하는 지정학적 긴장 상태를 나타냅니다.`;
      return `현재 지수(${val.toFixed(1)})는 평상시 평균 수준(약 100 내외)으로 비교적 안정된 상태입니다.`;
    case 'krw_usd':
      if (val >= 1800) return `현재 환율(${val.toFixed(1)}원)은 1997년 IMF 외환위기 당시(최고 약 1,964원) 수준의 초고위험 수치입니다.`;
      if (val >= 1500) return `현재 환율(${val.toFixed(1)}원)은 2008년 글로벌 금융위기 당시 수준에 근접한 초고위험 수치입니다.`;
      if (val >= 1400) return `현재 환율(${val.toFixed(1)}원)은 2022년 하반기 고금리 쇼크(약 1,440원)에 근접한 고위험 수치입니다.`;
      if (val >= 1350) return `현재 환율(${val.toFixed(1)}원)은 2020년 3월 코로나19 팬데믹 직후(약 1,280원)보다 월등히 높은 달러 강세 수치입니다.`;
      if (val >= 1200) return `현재 환율(${val.toFixed(1)}원)은 평시 평균 수준(약 1,150~1,200원)을 웃도는 수치입니다.`;
      return `현재 환율(${val.toFixed(1)}원)은 평시 평균 수준으로 안정적인 편입니다.`;
    case 'wti':
      if (val >= 120) return `현재 유가(${val.toFixed(1)}$)는 2022년 3월 우크라이나 침공 직후(약 123$)에 근접한 초고유가 상태입니다.`;
      if (val >= 90) return `현재 유가(${val.toFixed(1)}$)는 2014년 셰일 혁명 이전의 고유가 시대에 준하는 높은 수치입니다.`;
      if (val >= 60) return `현재 유가(${val.toFixed(1)}$)는 과거 10년간의 평시 평균 수준(약 60~80$) 범위 내에 있습니다.`;
      return `현재 유가(${val.toFixed(1)}$)는 평균을 하회하는 저유가 상태입니다.`;
    case 'cpi':
      if (val >= 120) return `현재 한국 소비자물가 총지수(${val.toFixed(1)})는 기준 연도인 2020년(100) 대비 20% 이상 물가가 상승한 매우 높은 수준입니다.`;
      if (val >= 110) return `현재 한국 소비자물가 총지수(${val.toFixed(1)})는 기준 연도인 2020년(100) 대비 10% 이상 물가가 상승한 수준입니다.`;
      if (val >= 100) return `현재 한국 소비자물가 총지수(${val.toFixed(1)})는 기준 연도인 2020년(100)을 상회하는 수준입니다.`;
      return `현재 한국 소비자물가 총지수(${val.toFixed(1)})는 기준 연도인 2020년(100) 이하의 수준입니다.`;
    case 'fed':
      if (val >= 4.5) return `현재 미 10년 국채(${val.toFixed(1)}%)는 2023년 10월 고금리 장기화 우려 시기(약 4.9%)에 근접한 매우 높은 수치입니다.`;
      if (val >= 4.0) return `현재 미 10년 국채(${val.toFixed(1)}%)는 2022년 하반기 급격한 금리 인상기(약 4.0% 이상) 수준의 높은 수치입니다.`;
      if (val >= 3.0) return `현재 미 10년 국채(${val.toFixed(1)}%)는 2018년 미 연준의 정상화 시기(약 3.2%)와 유사한 수치입니다.`;
      if (val >= 1.5) return `현재 미 10년 국채(${val.toFixed(1)}%)는 평상시 수준을 유지하고 있습니다.`;
      return `현재 미 10년 국채(${val.toFixed(1)}%)는 2020년 코로나19 직후(약 0.5%)에 가까운 이례적으로 낮은 수치입니다.`;
    default:
      return "과거 평균과 비교한 데이터입니다.";
  }
}

/** 지수별 설명 반환 함수 */
export function getIndexDescription(key) {
  switch (key) {
    case 'ai_gpr':
      return "글로벌 정치·군사적 긴장과 위험도를 실시간 뉴스로 분석하여 평상시를 100 기준으로 수치화한 지표입니다.";
    case 'krw_usd':
      return "1달러를 원화로 교환할 때 지불해야 하는 원화의 가치로, 기업의 수출입과 국내 체감 물가에 큰 영향을 미칩니다.";
    case 'wti':
      return "서부 텍사스산 원유 1배럴당 달러 가격으로, 국제 유가의 기준이 되며 주유소 기름값과 운송비에 직접적인 영향을 미칩니다.";
    case 'cpi':
      return "2020년을 100으로 기준 삼아, 국내 소비자가 구입하는 상품과 서비스의 전반적인 물가 수준을 측정한 총지수입니다.";
    case 'fed':
      return "미국 재무부가 발행하는 만기 10년짜리 국채로, 글로벌 장기 경제 전망의 기준점 역할을 합니다.";
    default:
      return "거시 경제를 판단하는 주요 참고 지표입니다.";
  }
}
