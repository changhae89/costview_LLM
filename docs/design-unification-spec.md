# Costview 디자인 통일 사양서

> 기준: `front_web` (Vite + React + Tailwind, 서민 친화적 디자인 완성본)  
> 대상: `front_app` (Expo React Native)  
> 근거: `.claude/skills/skills/frontend-design/SKILL.md`

---

## 1. 현황 분석 — 두 앱의 차이

| 항목 | front_web (기준) | front_app (현재) | 불일치 |
|------|-----------------|-----------------|--------|
| 주색상 | 오렌지 `#F97316` | 민트 `#0D9488` | ❌ |
| 헤더 배경 | 흰색 + 하단 테두리 | 민트 배경색 | ❌ |
| 상승(Up) 색상 | 빨강 `#EF4444` | 주황 `#D85A30` | ❌ |
| 하락(Down) 색상 | 초록 `#22C55E` | 민트초록 `#1D9E75` | ❌ |
| 화면 배경 | 크림 `#FFFBF7` | 청회색 `#F4F7FA` | ❌ |
| 탭 활성 색상 | 오렌지 `#F97316` | 민트 `#0D9488` | ❌ |
| 태그 상승 배경 | `#FEE2E2` | `#FCEBEB` | ❌ |
| 태그 상승 텍스트 | `#B91C1C` | `#791F1F` | ❌ |
| 태그 하락 배경 | `#DCFCE7` | `#EAF3DE` | ❌ |
| 태그 하락 텍스트 | `#15803D` | `#27500A` | ❌ |
| 강도 점(high) | `#EF4444` | `#D85A30` | ❌ |
| 강도 점(med) | `#F59E0B` | `#EF9F27` | ❌ |
| 폰트 | Plus Jakarta Sans + DM Mono | 기본 RN 폰트 | ❌ |
| 카드 모서리 | 12px (`rounded-xl`) | 14px | △ |

---

## 2. 통일 디자인 토큰

### 2-1. 색상 (`front_app/src/constants/colors.js`)

```js
export const COLORS = {
  // ── Primary (오렌지 계열) ───────────────────────────
  primary:        '#F97316',   // 주색상 (탭 활성, 강조)
  primaryDark:    '#EA580C',   // 진한 주색상 (활성 NavLink 등)
  primaryAccent:  '#FED7AA',   // 연한 주색상 (배지, 게이지 바)
  surface:        '#FFF7ED',   // 카드 배경 강조 영역 (orange-50)

  // ── 방향 (소비자 직관: 상승=나쁨=빨강, 하락=좋음=초록) ──
  up:             '#EF4444',   // 상승 — 빨강
  down:           '#22C55E',   // 하락 — 초록
  neutral:        '#9CA3AF',   // 중립 — 회색
  upLight:        '#FEE2E2',   // 상승 배경
  downLight:      '#DCFCE7',   // 하락 배경

  // ── 태그 ──────────────────────────────────────────
  tagUpBg:        '#FEE2E2',
  tagUpText:      '#B91C1C',
  tagDownBg:      '#DCFCE7',
  tagDownText:    '#15803D',

  // ── 강도 점 ───────────────────────────────────────
  dotHigh:        '#EF4444',
  dotMed:         '#F59E0B',
  dotLow:         '#E5E7EB',

  // ── 차트 시리즈 ───────────────────────────────────
  warning:        '#F59E0B',
  series3:        '#6366F1',
  series4:        '#EC4899',

  // ── 배경 / 레이아웃 ───────────────────────────────
  screenBg:       '#FFFBF7',   // 전체 배경 (크림)
  white:          '#FFFFFF',
  border:         '#F3F4F6',

  // ── 헤더 (흰색 + 테두리) ──────────────────────────
  headerBg:       '#FFFFFF',
  headerBorder:   '#F3F4F6',
  headerText:     '#111827',
  headerMuted:    '#6B7280',

  // ── 탭 ────────────────────────────────────────────
  tabActive:      '#F97316',
  tabInactive:    '#9CA3AF',

  // ── 텍스트 ────────────────────────────────────────
  textPrimary:    '#111827',
  textMuted:      '#6B7280',
  textLight:      '#9CA3AF',

  // ── 신뢰도 (ReliabilityBadge) ─────────────────────
  highBg:         '#FFF7ED',   // orange-50
  highText:       '#EA580C',   // orange-600
  medBg:          '#FFFBEB',   // amber-50
  medText:        '#92400E',   // amber-800
  lowBg:          '#F9FAFB',
  lowText:        '#6B7280',
};
```

### 2-2. 방향 상수 (`front_app/src/constants/category.js`)

```js
export const DIRECTION_MAP = {
  up:      { label: '▲ 상승', color: '#EF4444', dotColor: '#EF4444' },
  down:    { label: '▼ 하락', color: '#22C55E', dotColor: '#22C55E' },
  neutral: { label: '─ 중립', color: '#9CA3AF', dotColor: '#9CA3AF' },
};

export const MAGNITUDE_MAP = {
  high:   { label: '강함', dots: ['#EF4444', '#EF4444', '#EF4444'] },
  medium: { label: '보통', dots: ['#F59E0B', '#F59E0B', '#E5E7EB'] },
  low:    { label: '약함', dots: ['#E5E7EB', '#E5E7EB', '#E5E7EB'] },
};

export function getReliabilityBadge(r) {
  if (r >= 0.8) return { label: `${Math.round(r * 100)}%`, bg: '#FFF7ED', color: '#EA580C' };
  if (r >= 0.5) return { label: `${Math.round(r * 100)}%`, bg: '#FFFBEB', color: '#92400E' };
  if (r >= 0.3) return { label: `${Math.round(r * 100)}%`, bg: '#F9FAFB', color: '#6B7280' };
  return null;
}
```

### 2-3. 타이포그래피

React Native에서 웹 폰트(`Plus Jakarta Sans`, `DM Mono`) 사용:

```bash
# 설치
npx expo install @expo-google-fonts/plus-jakarta-sans @expo-google-fonts/dm-mono expo-font
```

```js
// App.jsx — 폰트 로드
import { useFonts } from 'expo-font';
import {
  PlusJakartaSans_400Regular,
  PlusJakartaSans_500Medium,
  PlusJakartaSans_700Bold,
} from '@expo-google-fonts/plus-jakarta-sans';
import { DMMono_400Regular } from '@expo-google-fonts/dm-mono';

// fontFamily 적용 규칙
// - 본문, 레이블, 버튼: 'PlusJakartaSans_700Bold' / '_500Medium' / '_400Regular'
// - 숫자(환율, 지수 등): 'DMMono_400Regular'
```

---

## 3. 컴포넌트별 변경 사항

### 3-1. `front_app/src/constants/colors.js`
- **전체 교체** → 위 2-1 토큰으로 대체

### 3-2. `front_app/src/constants/category.js`
- `DIRECTION_MAP` color/dotColor 값 교체 → 2-2 참고
- `MAGNITUDE_MAP` dots 배열 교체 → 2-2 참고
- `getReliabilityBadge` bg/color 값 교체 → 2-2 참고

### 3-3. `front_app/src/screens/DashboardScreen.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `styles.header backgroundColor` | `COLORS.headerBg` (민트) | `COLORS.headerBg` (흰색, 토큰 교체로 자동 반영) |
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `StatusBar backgroundColor` | `COLORS.headerBg` | `COLORS.headerBg` |
| `styles.headerTitle color` | `COLORS.headerText` | 토큰 교체로 자동 반영 |
| `styles.riskCard backgroundColor` | `rgba(255,255,255,0.10)` | `#FFFFFF` + border |
| `styles.riskLabel color` | `rgba(255,255,255,0.9)` | `COLORS.textMuted` |
| `styles.riskValue color` | `COLORS.headerText` | `COLORS.textPrimary` |
| `styles.screenBg` | `#F4F7FA` | `COLORS.screenBg` (크림) |
| 게이지 바 색상 로직 | 파랑/노랑/주황/빨강 4단계 | `COLORS.primaryAccent` 단색 |
| `changeColor` 계산 | `#FF8A7A` / `#6EE7B7` | `COLORS.up` / `COLORS.down` |

### 3-4. `front_app/src/screens/NewsListScreen.jsx`
- 검색바/필터 활성 색상: `COLORS.headerBg` → `COLORS.primary`
- 상단 헤더 배경: 민트 → 흰색

### 3-5. `front_app/src/screens/RiskScreen.jsx`
- 헤더 배경: 민트 → 흰색
- 탭 활성 색상: `COLORS.tabActive` (토큰 교체로 자동 반영)

### 3-6. `front_app/src/screens/SettingsScreen.jsx`
- 헤더 배경: 민트 → 흰색

### 3-7. `front_app/src/components/LoadingView.jsx`
- 스피너 색상: `COLORS.headerBg` → `COLORS.primary`

---

## 4. 구현 순서

```
1단계 — 토큰 교체 (자동 전파)
  └── colors.js 전체 교체
  └── category.js DIRECTION_MAP, MAGNITUDE_MAP, getReliabilityBadge 교체
      → 대부분의 컴포넌트는 토큰만 바꾸면 자동 반영

2단계 — 하드코딩 값 수정
  └── DashboardScreen.jsx 헤더/RiskCard 인라인 색상 교체
  └── 각 Screen의 StatusBar barStyle 수정

3단계 — 폰트 적용 (선택)
  └── expo-google-fonts 패키지 설치
  └── App.jsx 폰트 로드
  └── 주요 컴포넌트 fontFamily 적용

4단계 — 검증
  └── 각 화면 실행 후 시각 확인
  └── 상승/하락 색상이 web과 동일한지 확인
  └── 헤더가 흰색 + 테두리로 전환됐는지 확인
```

---

## 5. 검증 체크리스트

| 항목 | 확인 방법 |
|------|-----------|
| 주색상이 오렌지(`#F97316`)로 통일 | 탭 활성 색상, 버튼 확인 |
| 헤더가 흰색 + 하단 테두리 | DashboardScreen, NewsListScreen |
| 상승 = 빨강(`#EF4444`), 하락 = 초록(`#22C55E`) | DirectionDot, CategoryRow, 태그 |
| 화면 배경이 크림(`#FFFBF7`) | 모든 스크린 배경 |
| 태그 색상이 web과 동일 | up태그: `#FEE2E2`/`#B91C1C`, down태그: `#DCFCE7`/`#15803D` |
| 신뢰도 뱃지가 오렌지 계열 | ReliabilityBadge (high: `#FFF7ED`/`#EA580C`) |
| 강도 점이 web과 동일 | MagnitudeDots (high: `#EF4444`, med: `#F59E0B`) |
| `expo start`로 앱 실행 오류 없음 | iOS/Android 시뮬레이터 |

---

## 6. 변경 대상 파일 목록

```
front_app/src/constants/colors.js          ← 전체 교체 (핵심)
front_app/src/constants/category.js        ← DIRECTION_MAP, MAGNITUDE_MAP, getReliabilityBadge
front_app/src/screens/DashboardScreen.jsx  ← 헤더, RiskCard, StatusBar 하드코딩 수정
front_app/src/screens/NewsListScreen.jsx   ← 헤더, 검색 활성 색상
front_app/src/screens/RiskScreen.jsx       ← 헤더
front_app/src/screens/SettingsScreen.jsx   ← 헤더
front_app/src/components/LoadingView.jsx   ← 스피너 색상
front_app/App.jsx                          ← 폰트 로드 (3단계, 선택)
```

---

## 7. 참고 — 변경하지 않는 것

- `front_app`의 **레이아웃 구조** (스크롤 방식, 바텀 탭, 바텀 시트 등) → 모바일 UX에 최적화돼 있어 유지
- **카드 모서리 반경** (14px) → 모바일 터치 UX상 웹(12px)보다 약간 크게 유지해도 무방
- **섀도 스타일** (`elevation`, `shadowOpacity`) → 플랫폼별 네이티브 스타일 유지
- `front_web`의 **Tailwind 클래스** → 웹 전용, 앱에 적용 불가
