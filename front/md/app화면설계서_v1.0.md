# 물가 레이더 — 앱 화면 설계서 (App Screen Specification)

> **작성일**: 2026-04-10  
> **버전**: v1.0  
> **목적**: Cursor AI가 React Native 또는 Flutter 기반으로 구현할 수 있도록 작성된 앱 화면 설계서  
> **스택 가정**: React Native + Supabase JS Client + React Navigation (Bottom Tab)  
> **참고 파일**: `screen_spec_for_cursor.md` (DB 스키마·쿼리·데이터 처리 규칙)

---

## 목차

1. [앱 공통 사항](#1-앱-공통-사항)
2. [SCR-001 대시보드](#scr-001-대시보드)
3. [SCR-002 뉴스 목록 & 상세](#scr-002-뉴스-목록--상세)
4. [SCR-003 품목별 물가 예측](#scr-003-품목별-물가-예측)
5. [SCR-004 리스크 지수](#scr-004-리스크-지수)
6. [공통 컴포넌트](#6-공통-컴포넌트)
7. [네비게이션 구조](#7-네비게이션-구조)
8. [데이터 처리 규칙](#8-데이터-처리-규칙)

---

## 1. 앱 공통 사항

### 디바이스 기준
- 기준 해상도: 390 × 844px (iPhone 14 기준)
- Safe Area: 상단 44px (Status Bar), 하단 34px (Home Indicator) 확보
- 하단 탭 바 높이: 83px (탭 영역 49px + 하단 Safe Area 34px)

### 컬러 시스템

| 용도 | 값 | 비고 |
|------|-----|------|
| 헤더 배경 | `#1E3A5F` | 네이비 |
| 헤더 서브 강조 | `#5BB3D8` | 스카이블루 |
| 헤더 텍스트 | `#FFFFFF` | |
| 헤더 뮤트 텍스트 | `#7FA3C0` | |
| 상승 (up) | `#D85A30` | 빨강-주황 |
| 하락 (down) | `#1D9E75` | 초록 |
| 중립 (neutral) | `#B4B2A9` | 회색 |
| 신뢰도 高 배경 | `#FCEBEB` | |
| 신뢰도 高 텍스트 | `#791F1F` | |
| 신뢰도 中 배경 | `#FAEEDA` | |
| 신뢰도 中 텍스트 | `#633806` | |
| 신뢰도 低 배경 | `#F1EFE8` | |
| 신뢰도 低 텍스트 | `#5F5E5A` | |

### 카테고리 한국어 매핑

```typescript
// constants/category.ts
export const CATEGORY_MAP: Record<string, string> = {
  fuel:    '연료 · 에너지',
  travel:  '교통 · 여행',
  utility: '전기 · 가스 · 수도',
  dining:  '식음료',
  neutral: '기타',
};

export const DIRECTION_MAP: Record<string, { label: string; color: string; dotColor: string }> = {
  up:      { label: '▲ 상승', color: '#D85A30', dotColor: '#D85A30' },
  down:    { label: '▼ 하락', color: '#1D9E75', dotColor: '#1D9E75' },
  neutral: { label: '─ 중립', color: '#888780', dotColor: '#B4B2A9' },
};

export const MAGNITUDE_MAP: Record<string, { label: string; dots: string[] }> = {
  high:   { label: '강함',  dots: ['#D85A30', '#D85A30', '#D85A30'] },
  medium: { label: '보통',  dots: ['#EF9F27', '#EF9F27', '#E5E7EB'] },
  low:    { label: '약함',  dots: ['#E5E7EB', '#E5E7EB', '#E5E7EB'] },
};
```

### 신뢰도 뱃지

```typescript
export function getReliabilityBadge(r: number) {
  if (r >= 0.8) return { label: `高 ${Math.round(r * 100)}%`, bg: '#FCEBEB', color: '#791F1F' };
  if (r >= 0.5) return { label: `中 ${Math.round(r * 100)}%`, bg: '#FAEEDA', color: '#633806' };
  if (r >= 0.3) return { label: `低 ${Math.round(r * 100)}%`, bg: '#F1EFE8', color: '#5F5E5A' };
  return null; // 0.3 미만 비표시
}
```

---

## SCR-001 대시보드

### 목적
지정학 리스크 지수, 카테고리별 가격 영향, 최신 뉴스를 한눈에 확인

### 화면 구조

```
┌─────────────────────────┐
│ Status Bar (44px)        │  #1E3A5F
├─────────────────────────┤
│ Header                   │  #1E3A5F · padding 10px 16px
│  물가 레이더              │  fontSize 17 · white · bold
│  WAR PRICE RADAR         │  fontSize 10 · #5BB3D8
│  [기준일 2026-03-31]     │  우측 상단 뱃지
│                          │
│  ┌──────┐┌──────┐┌─────┐│  리스크 카드 3개 (flex row)
│  │AI GPR││석유차질││비석유││
│  │250.6 ││1,717 ││154.7││
│  │▲+18.4││▲+347 ││▼-42.4││
│  └──────┘└──────┘└─────┘│
├─────────────────────────┤
│ ScrollView (Body)        │  backgroundColor: #F4F7FA
│                          │
│  카테고리별 가격 영향      │  section label
│  ┌─────────────────────┐│
│  │● 교통·여행  ▲+22~28%││  카드 rows
│  │● 연료·에너지 ▼-2~5% ││
│  │● 전기·가스  ▼약-5%  ││
│  │● 식음료    ─ 중립   ││
│  └─────────────────────┘│
│                          │
│  최신 뉴스               │  section label
│  ┌─────────────────────┐│
│  │● 뉴스 제목 1   [高]  ││
│  │  요약 1줄...         ││
│  │  [▲fuel][▲oil][war] ││
│  ├─────────────────────┤│
│  │● 뉴스 제목 2   [中]  ││
│  │  ...                 ││
│  └─────────────────────┘│
├─────────────────────────┤
│ Bottom Tab Bar           │  backgroundColor: white
│ [대시보드●][뉴스][예측][리스크] │
└─────────────────────────┘
```

### 컴포넌트 1 — 리스크 지수 카드 (3개, Flex Row)

| 속성 | 값 |
|------|-----|
| 배경 | `rgba(255,255,255,0.10)` |
| 보더 반경 | 12px |
| 패딩 | 9px 10px |
| 레이블 | fontSize 9 · `rgba(255,255,255,0.6)` |
| 수치 | fontSize 18 · white · bold |
| 바 | 높이 3px · 배경 `rgba(255,255,255,0.15)` |
| 전일 대비 | fontSize 10 · 상승 `#FF8A7A` / 하락 `#6EE7B7` |

**Supabase 쿼리**:
```typescript
// 최신 2건으로 전일 대비 계산
const { data } = await supabase
  .from('indicator_daily_logs')
  .select('ai_gpr_index, oil_disruptions, gpr_original, non_oil_gpr, reference_date')
  .order('reference_date', { ascending: false })
  .limit(2);

const latest = data[0];
const prev   = data[1];
const aiChange = (latest.ai_gpr_index - prev.ai_gpr_index).toFixed(1);
```

### 컴포넌트 2 — 카테고리별 가격 영향 카드

| 속성 | 값 |
|------|-----|
| 배경 | white |
| 보더 반경 | 14px |
| 각 행 패딩 | 11px 14px |
| 구분선 | `0.5px solid #E5E7EB` |
| 방향 닷 | 직경 8px 원 · direction 색상 적용 |
| 카테고리명 | fontSize 13 · bold |
| 건수 | fontSize 10 · muted |
| 변동폭 | fontSize 13 · bold · direction 색상 |
| 강도 닷 | 직경 6px 원 · 3개 · magnitude 색상 |

**Supabase 쿼리**:
```typescript
const { data } = await supabase
  .from('causal_chains')
  .select(`
    category, direction, magnitude,
    change_pct_min, change_pct_max,
    news_analyses!inner(reliability, created_at)
  `)
  .neq('direction', 'neutral')
  .gte('news_analyses.reliability', 0.3);
// 프론트에서 category별 그룹핑 후 대표 direction, 평균 변동폭 계산
```

### 컴포넌트 3 — 최신 뉴스 카드

| 속성 | 값 |
|------|-----|
| 배경 | white |
| 보더 반경 | 14px |
| 각 항목 패딩 | 11px 14px |
| 방향 닷 | 직경 7px · 왼쪽 정렬 |
| 제목 | fontSize 12 · bold · 2줄 말줄임 |
| 요약 | fontSize 11 · muted · 1줄 말줄임 |
| 태그 | fontSize 10 · 상승 `#FCEBEB/#791F1F` · 하락 `#EAF3DE/#27500A` · 키워드 gray |

**Supabase 쿼리**:
```typescript
const { data } = await supabase
  .from('news_analyses')
  .select(`
    summary, reliability,
    raw_news:raw_news_id(title, keyword, increased_items, decreased_items)
  `)
  .gte('reliability', 0.3)
  .order('created_at', { ascending: false })
  .limit(5);
```

---

## SCR-002 뉴스 목록 & 상세

### 목적
수집된 뉴스 목록 탐색 및 AI 분석 결과 확인

### 화면 구조 — 목록

```
┌─────────────────────────┐
│ Status Bar               │  #1E3A5F
├─────────────────────────┤
│ Header                   │  #1E3A5F
│  뉴스                    │  fontSize 17
│  WAR PRICE RADAR         │  fontSize 10
│  ┌──────────────────┐[≡]│  검색창 + 필터 아이콘
│  │🔍 뉴스·키워드 검색│   │
│  └──────────────────┘   │
│  [전체][▲상승][▼하락]     │  수평 스크롤 필터 칩
│  [연료·에너지][교통·여행] │
│  [전기·가스][신뢰도 高]   │
├─────────────────────────┤
│ [8건]          [최신순↕] │  list bar
├─────────────────────────┤
│ ScrollView               │  padding 10px
│  ┌─────────────────────┐│
│  │● 뉴스 제목 (2줄)  [高]││  카드 (borderRadius 14)
│  │  요약 1줄...         ││
│  │  날짜 [▲fuel][war]  ││
│  └─────────────────────┘│
│  (반복)                  │
├─────────────────────────┤
│ Bottom Tab               │
└─────────────────────────┘
```

### 화면 구조 — 상세 (슬라이드 전환)

```
┌─────────────────────────┐
│ Status Bar               │  #1E3A5F
├─────────────────────────┤
│ Detail Header            │  #1E3A5F
│  ← 뉴스 목록             │  back 버튼
│  뉴스 한국어 제목          │  fontSize 14 · white · bold
│  원문 영문 제목 (이탤릭)   │  fontSize 10 · rgba(white,0.5)
│  날짜 [신뢰도高] [↑상승] [카테고리] │
├─────────────────────────┤
│ ScrollView               │
│  ┌─────────────────────┐│  AI 분석 요약 카드
│  │AI 분석 요약           ││
│  │  한국어 요약 텍스트    ││
│  │  신뢰도 ━━━━━━░ 90% ││
│  └─────────────────────┘│
│  ┌─────────────────────┐│  관련 지표 카드
│  │관련 지표              ││
│  │  [WTI 유가]           ││
│  └─────────────────────┘│
│  ┌─────────────────────┐│  영향 품목 카드
│  │영향 품목              ││
│  │  ▲급등  │ ▼급락      ││
│  │  [fuel] │ [없음]     ││
│  └─────────────────────┘│
│  ┌─────────────────────┐│  키워드 카드
│  │키워드                 ││
│  │  [war][fuel][oil]... ││
│  └─────────────────────┘│
│  ┌─────────────────────┐│  CTA 버튼
│  │→ 인과관계 상세 보기   ││  bg #1E3A5F · white
│  └─────────────────────┘│
├─────────────────────────┤
│ Bottom Tab               │
└─────────────────────────┘
```

### 핵심 인터랙션

| 동작 | 결과 |
|------|------|
| 뉴스 카드 탭 | 상세 화면 슬라이드 인 (translateX: 100% → 0) |
| ← 뉴스 목록 탭 | 슬라이드 아웃 (translateX: 0 → 100%) |
| 필터 칩 탭 | 토글 (재탭 시 해제), 목록 즉시 필터링 |
| 검색 입력 | 제목 + 키워드 실시간 필터 |
| 정렬 버튼 탭 | 최신순 ↔ 오래된순 전환 |

### 필터 칩 상태

```typescript
type FilterState = {
  query: string;           // 검색어
  category: string;        // '' | 'fuel' | 'travel' | 'utility' | 'dining'
  direction: string;       // '' | 'up' | 'down' | 'neutral'
  minReliability: number;  // 0 | 0.3 | 0.5 | 0.8
};
```

---

## SCR-003 품목별 물가 예측

### 목적
causal_chains 기반 카테고리별 가격 변동 예측 정보 제공

### 화면 구조 — 목록

```
┌─────────────────────────┐
│ Status Bar               │  #1E3A5F
├─────────────────────────┤
│ Header                   │  #1E3A5F
│  품목 예측               │  fontSize 17
│  카테고리별 가격 변동      │  fontSize 10 · #5BB3D8
│  [전체][▲상승][▼하락]     │  수평 스크롤 필터 칩
│  [연료·에너지][교통·여행] │
│  [전기·가스][식음료]      │
├─────────────────────────┤
│ ScrollView               │  padding 10px
│                          │
│  카테고리별 예측 (4건)    │  section label
│                          │
│  ┌─────────────────────┐│  카드 (borderRadius 14)
│  │ travel               ││  영문 · fontSize 10 · muted
│  │ 교통 · 여행           ││  fontSize 14 · bold
│  │ ▲ +22.2 ~ +28.6%    ││  fontSize 20 · bold · #D85A30
│  │ 항공 수하물·항공권 상승││  fontSize 11 · muted
│  │          [강함] ●●●  ││  우측: 강도뱃지 + 도트
│  ├─────────────────────┤│
│  │ 항공사 수하물 요금...  │  2건 ││  하단: 인과관계 미리보기
│  └─────────────────────┘│
│  (반복)                  │
├─────────────────────────┤
│ Bottom Tab               │
└─────────────────────────┘
```

### 화면 구조 — 상세 (슬라이드 전환)

```
┌─────────────────────────┐
│ Status Bar               │  #1E3A5F
├─────────────────────────┤
│ Detail Header            │  #1E3A5F
│  ← 품목 예측             │  back 버튼
│  교통 · 여행             │  fontSize 15 · white
│  ▲ +22.2 ~ +28.6%       │  fontSize 26 · #FF8A7A
│  [강함] [2건의 인과관계] │
├─────────────────────────┤
│ ScrollView               │
│  ┌─────────────────────┐│  인과관계 체인 카드
│  │인과관계 체인           ││
│  │  [이벤트명...] → [결과]││  flow 노드
│  │  메커니즘 설명 텍스트  ││
│  │  ─────────────────  ││
│  │  [이벤트명...] → [결과]││
│  │  메커니즘 설명 텍스트  ││
│  └─────────────────────┘│
│  ┌─────────────────────┐│  요약 카드
│  │요약                   ││
│  │  항공 수하물·항공권    ││
│  │  총 2건의 뉴스 분석    ││
│  └─────────────────────┘│
├─────────────────────────┤
│ Bottom Tab               │
└─────────────────────────┘
```

### 카드 컴포넌트 스펙

| 요소 | 스펙 |
|------|------|
| 카드 배경 | white |
| 카드 보더 반경 | 14px |
| 상단 보더 | 3px solid · direction 색상 (up: #D85A30, down: #1D9E75, neutral: #E5E7EB) |
| 영문 카테고리 | fontSize 10 · muted |
| 한국어 카테고리 | fontSize 14 · bold |
| 변동폭 | fontSize 20 · bold · direction 색상 |
| 설명 | fontSize 11 · muted |
| 강도 뱃지 | fontSize 10 · rounded · high:#FCEBEB/#791F1F, medium:#FAEEDA/#633806, low:#F1EFE8/#5F5E5A |
| 강도 도트 | 직경 8px 원 3개 |
| 하단 구분선 | 0.5px |
| 인과관계 미리보기 | fontSize 11 · muted · 1줄 말줄임 |
| 건수 뱃지 | fontSize 10 · gray bg |

### 인과관계 플로우 노드

```
[이벤트 노드] → [결과 노드]
```

| 노드 | 스타일 |
|------|--------|
| 이벤트 노드 | bg `#FCEBEB` · color `#791F1F` · borderRadius 6 · fontSize 11 |
| 결과 노드 (up) | bg `#FCEBEB` · color `#791F1F` · bold |
| 결과 노드 (down) | bg `#EAF3DE` · color `#27500A` · bold |
| 화살표 | `→` · fontSize 11 · muted |
| 메커니즘 텍스트 | fontSize 11 · muted · 2줄 말줄임 |

---

## SCR-004 리스크 지수

### 목적
AI_GPR, 석유 공급 차질 지수를 일간/월간 차트로 시각화

### 화면 구조

```
┌─────────────────────────┐
│ Status Bar               │  #1E3A5F
├─────────────────────────┤
│ Header                   │  #1E3A5F
│  리스크 지수             │  fontSize 17
│  지정학 위험 트렌드       │  fontSize 10 · #5BB3D8
│  [일간●] [월간]          │  탭 (pill style)
│  [10일●] [20일] [전체]   │  범위 칩
├─────────────────────────┤
│ ScrollView               │  padding 10px
│                          │
│  ┌─────────┬───────────┐│  통계 카드 2×2 grid
│  │AI GPR   │석유 공급   ││
│  │ 250.6   │ 1,717     ││  fontSize 20 · bold
│  │ ▲+18.4  │ ▲+347     ││  fontSize 11 · up/dn 색상
│  ├─────────┼───────────┤│
│  │기간 최고 │기간 최저   ││
│  │ 345.8   │ 170.8     ││
│  │2026-03-28│2026-03-22││  fontSize 10 · muted
│  └─────────┴───────────┘│
│                          │
│  ┌─────────────────────┐│  차트 카드
│  │일간 AI GPR 지수 추이  ││  fontSize 12 · bold
│  │2026-03-22~03-31      ││  fontSize 10 · muted
│  │─ AI GPR  ─ 석유(÷10)││  범례
│  │─ 기존GPR ─ 비석유    ││
│  │  [Line Chart]        ││  높이 180px
│  │  * 석유 공급 차질 지수││  note
│  │  는 ÷10 표시          ││
│  └─────────────────────┘│
├─────────────────────────┤
│ Bottom Tab               │
└─────────────────────────┘
```

### 탭 & 범위 칩 스타일

| 상태 | 스타일 |
|------|--------|
| 탭 기본 | border 1px `rgba(white,0.2)` · color `rgba(white,0.65)` |
| 탭 활성 | bg white · color `#1E3A5F` · bold |
| 범위 칩 기본 | border `rgba(white,0.15)` · color `rgba(white,0.5)` |
| 범위 칩 활성 | border `rgba(white,0.5)` · color `rgba(white,0.9)` |

### 차트 시리즈 설정

```typescript
const SERIES = [
  { key: 'ai_gpr_index',    label: 'AI GPR',       color: '#D85A30', width: 2,   dash: false },
  { key: 'oil_disruptions', label: '석유 차질(÷10)', color: '#EF9F27', width: 1.5, dash: false },
  { key: 'gpr_original',    label: '기존 GPR',      color: '#888780', width: 1,   dash: true  },
  { key: 'non_oil_gpr',     label: '비석유',         color: '#2E86AB', width: 1.5, dash: false },
];
// oil_disruptions는 표시 시 ÷10 처리
```

### Supabase 쿼리

```typescript
// 일간
const { data: daily } = await supabase
  .from('indicator_daily_logs')
  .select('ai_gpr_index, oil_disruptions, gpr_original, non_oil_gpr, reference_date')
  .order('reference_date', { ascending: true });

// 월간 (컬럼명 대소문자 주의)
const { data: monthly } = await supabase
  .from('indicator_logs')
  .select('"AI_GPR_Index", oil_disruptions, gpr_original, non_oil_gpr, reference_date')
  .order('reference_date', { ascending: true });
```

### 통계 계산

```typescript
function calcStats(data: any[], key: string) {
  const vals = data.map(d => d[key]);
  const last = vals[vals.length - 1];
  const prev = vals[vals.length - 2];
  const change = parseFloat((last - prev).toFixed(1));
  const max = Math.max(...vals);
  const min = Math.min(...vals);
  const maxDate = data[vals.indexOf(max)].reference_date;
  const minDate = data[vals.indexOf(min)].reference_date;
  return { last, change, max, min, maxDate, minDate };
}
```

---

## 6. 공통 컴포넌트

### 하단 탭 바

| 탭 | 아이콘 | 라벨 | 화면 |
|----|--------|------|------|
| 1 | 바 차트 | 대시보드 | SCR-001 |
| 2 | 문서 | 뉴스 | SCR-002 |
| 3 | 꺾은선 | 품목 예측 | SCR-003 |
| 4 | 시계 원형 | 리스크 | SCR-004 |

```
높이: 83px (탭 49px + Safe Area 34px)
배경: white
상단 보더: 0.5px #E5E7EB
활성 아이콘 색상: #1E3A5F
비활성 아이콘 색상: #9CA3AF (opacity 0.4)
활성 라벨: fontSize 10 · #1E3A5F · bold
비활성 라벨: fontSize 10 · #9CA3AF
활성 인디케이터: 직경 4px 원 · #1E3A5F · 라벨 아래
```

### 방향 닷 (Direction Dot)

```
직경: 7~9px (화면에 따라 상이)
상승(up):      #D85A30
하락(down):    #1D9E75
중립(neutral): #B4B2A9
```

### 슬라이드 전환 애니메이션

```typescript
// React Native Animated 예시
const slideAnim = useRef(new Animated.Value(screenWidth)).current;

function openDetail() {
  Animated.timing(slideAnim, {
    toValue: 0,
    duration: 280,
    easing: Easing.bezier(0.4, 0, 0.2, 1),
    useNativeDriver: true,
  }).start();
}

function closeDetail() {
  Animated.timing(slideAnim, {
    toValue: screenWidth,
    duration: 280,
    easing: Easing.bezier(0.4, 0, 0.2, 1),
    useNativeDriver: true,
  }).start();
}
```

### 섹션 레이블

```
fontSize: 11px
fontWeight: 500
color: #6B7280 (muted)
letterSpacing: 0.3px
marginBottom: 8px
```

---

## 7. 네비게이션 구조

```
RootNavigator (Stack)
└── MainNavigator (Bottom Tab)
    ├── DashboardScreen          (SCR-001)
    ├── NewsNavigator (Stack)
    │   ├── NewsListScreen       (SCR-002 목록)
    │   └── NewsDetailScreen     (SCR-002 상세) ← 슬라이드 전환
    ├── PredictionNavigator (Stack)
    │   ├── PredictionListScreen (SCR-003 목록)
    │   └── PredictionDetailScreen (SCR-003 상세) ← 슬라이드 전환
    └── RiskScreen               (SCR-004)
```

---

## 8. 데이터 처리 규칙

### 필터링

| 조건 | 처리 |
|------|------|
| `raw_news.is_deleted = true` | 목록 제외 |
| `news_analyses.reliability < 0.3` | 뉴스 목록 노출 제외 |
| `causal_chains.direction = 'neutral'` | 급등락 집계 제외 |

### 이상값 처리

```typescript
// monthly_impact 이상값
export function formatMonthlyImpact(val: number | null): string {
  if (val === null || val === undefined) return '-';
  if (val === 0) return '단기';
  if (val > 999999) return '장기';
  return `${val}개월`;
}

// 지수 표시 (소수점 1자리)
export function formatIndex(val: number): string {
  return val.toFixed(1);
}

// 석유 공급 차질 지수 (차트 표시 시 ÷10)
export function normalizeOilDisruption(val: number): number {
  return parseFloat((val / 10).toFixed(1));
}
```

### 날짜 처리

```typescript
// reference_date가 text 타입 ('2026-03-31')
export function formatRefDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00Z');
  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
}
// 예: '3월 31일'
```

### 언어 처리

| 데이터 | 언어 | 표시 방법 |
|--------|------|----------|
| `raw_news.title` | 영문 | 원문 그대로 표시 (이탤릭 처리) |
| `news_analyses.summary` | 한국어 | 그대로 표시 (메인 제목으로 사용) |
| `causal_chains.event` | 한국어 | 그대로 표시 |
| `causal_chains.category` | 영문 소문자 | `CATEGORY_MAP`으로 변환 필수 |
| `causal_chains.direction` | 영문 소문자 | `DIRECTION_MAP`으로 변환 필수 |
| `causal_chains.magnitude` | 영문 소문자 | `MAGNITUDE_MAP`으로 변환 필수 |

---

*이 문서는 실제 Supabase 데이터를 기반으로 작성된 앱 화면 설계서입니다.*  
*DB 스키마·쿼리·처리 규칙 상세는 `screen_spec_for_cursor.md`를 참조하세요.*
