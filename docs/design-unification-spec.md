# Costview 디자인 통일 사양서

> 기준: `front_web` (Vite + React + Tailwind)  
> 대상: `front_app` (Expo React Native)  
> 철학 근거: `.claude/skills/skills/frontend-design/SKILL.md`  
> **소스 확인**: 변경 대상 전체 파일 직접 읽음 + 하드코딩 색상 전수 grep 완료

---

## 0. 디자인 철학 (SKILL.md 적용)

### 0-1. Aesthetic Direction — 서민 친화 따뜻한 정보 앱

| 항목 | 방향 |
|------|------|
| **Purpose** | 주부·직장인이 물가·경제 지표를 부담 없이 확인하는 앱. 전문가용 금융 앱처럼 차갑지 않게. |
| **Tone** | Warm & Trustworthy — 오렌지 계열의 따뜻함 + 크림 배경의 부드러움. 신뢰감과 친근함 공존. |
| **Differentiation** | "숫자를 읽어주는 친구" 같은 인터페이스. 상승=빨강/하락=초록의 직관적 색상 언어. 흰 헤더 + 오렌지 강조의 단순하고 일관된 시각 언어. |
| **Anti-pattern** | 민트/청록 계열 핀테크 클리셰, 과도한 그라디언트, generic 다크 테마 금지. |

### 0-2. Typography

- **본문·레이블·버튼**: `Plus Jakarta Sans` (400 / 500 / 700) — Inter·Roboto 대신 개성 있는 humanist sans
- **숫자(환율·지수·가격)**: `DM Mono` (400) — 모노스페이스로 수치 정렬과 신뢰감 확보
- **적용 우선순위**: 헤더 타이틀 → KPI 수치 → 카드 레이블 → 본문 순으로 적용
- **금지**: 기본 RN 시스템 폰트(`System`, 미지정 fontFamily)를 주요 UI 요소에 그대로 사용하지 않는다.

### 0-3. Color Philosophy

- **지배색 + 날카로운 강조색**: 크림 배경(`#FFFBF7`) 위에 오렌지(`#F97316`) 단색 강조. 색이 많아지면 신뢰감이 떨어진다.
- **방향 색상은 소비자 직관 우선**: 상승(가격 오름)=나쁨=빨강(`#EF4444`), 하락=좋음=초록(`#22C55E`). 금융권 관례(상승=초록)와 반대이며, 이 차이는 의도적이다.
- **토큰 시스템 강제**: 하드코딩 색상은 유지보수를 망친다. 모든 UI 색상은 `COLORS.*` 토큰을 통해서만 참조한다.

### 0-4. Motion (React Native)

- **원칙**: 애니메이션은 "있음을 알리기" 위해서가 아니라 "상태 전환을 명확히" 하기 위해 사용한다.
- **적용 대상**: 탭 전환 시 활성 인디케이터 슬라이드, 카드 로드 시 fade-in (`Animated.timing`), 풀-투-리프레시 오렌지 스피너.
- **금지**: 불필요한 bounce, 과도한 scale 애니메이션, 인터랙션 없는 장식 애니메이션.
- **구현 도구**: `Animated` API (RN 내장) 우선. 복잡한 시퀀스는 `react-native-reanimated`.

### 0-5. 이 사양서에서 의도적으로 제외한 항목

| SKILL.md 항목 | 제외 이유 |
|---------------|-----------|
| Spatial Composition (비대칭·레이아웃 파괴) | front_app 레이아웃은 모바일 UX 최적화 완료 상태, 구조 변경은 다음 이슈 |
| Backgrounds & Visual Details (그라디언트·노이즈 텍스처) | RN의 플랫폼 제약 + 서민 친화 앱 톤에 불필요 |
| 다크 테마 | 추후 이슈로 분리 |

---

## 1. 핵심 전제 (구현)

### 0-1. `COLORS.headerBg` 이중 용도 문제

현재 `colors.js`에 `primary` 토큰이 없다. `headerBg: '#0D9488'`(민트)가 두 역할을 겸한다.

| 역할 | 현재 | 변경 후 | 처리 방식 |
|------|------|---------|----------|
| 배경색 (header, modal 등) | `COLORS.headerBg` → 민트 | `COLORS.headerBg` → 흰색 | colors.js 토큰 교체로 자동 |
| 전경색 (활성 텍스트·스피너·tintColor) | `COLORS.headerBg` → 민트 | `COLORS.primary` → 오렌지 | **직접 교체 필요** |

### 0-2. 자동 반영 vs 직접 수정 구분

colors.js 교체만으로 처리되는 것:
- 헤더 `backgroundColor` (모든 스크린)
- `COLORS.screenBg`, `COLORS.tabActive`, `COLORS.tagUpBg` 등 토큰 참조

직접 수정해야 하는 것:
- 흰색 배경으로 바뀐 헤더 위의 **`rgba(255,255,255,...)` 인라인 색상** (보이지 않게 됨)
- **하드코딩된 `#1E3A5F` (남색)** — LoadingView, FilterChips
- **`changeColor`, `gaugeBarColor` 등 계산식 색상**

---

## 1. 현황 분석

| 항목 | front_web (기준) | front_app (현재) | 불일치 |
|------|-----------------|-----------------|--------|
| 주색상 토큰 | `primary: #F97316` | **없음** (`headerBg` 대용) | ❌ |
| 헤더 배경 | 흰색 + 테두리 | 민트 `#0D9488` | ❌ |
| StatusBar | dark-content | light-content | ❌ |
| 상승 색상 | `#EF4444` | `#D85A30` | ❌ |
| 하락 색상 | `#22C55E` | `#1D9E75` | ❌ |
| 화면 배경 | 크림 `#FFFBF7` | 청회색 `#F4F7FA` | ❌ |
| 활성 칩/탭 배경 | 오렌지 | 남색 `#1E3A5F` (FilterChips) | ❌ |
| 태그 up bg/text | `#FEE2E2` / `#B91C1C` | `#FCEBEB` / `#791F1F` | ❌ |
| 태그 down bg/text | `#DCFCE7` / `#15803D` | `#EAF3DE` / `#27500A` | ❌ |
| 강도 점 high | `#EF4444` | `#D85A30` | ❌ |
| 강도 점 med | `#F59E0B` | `#EF9F27` | ❌ |
| ai_gpr_index 레이블 | **글로벌 불안지수** | **글로벌 위기 지수** | ❌ 용어 불일치 → 섹션 8 참고 |
| 폰트 | Plus Jakarta Sans + DM Mono | 기본 RN | ❌ |
| 카드 모서리 | 12px | 14px | △ |

---

## 2. 통일 디자인 토큰 (`front_app/src/constants/colors.js` 전체 교체)

```js
export const COLORS = {
  // ── Primary (오렌지) — 신규 추가 ──────────────────────────
  primary:        '#F97316',
  primaryDark:    '#EA580C',
  primaryAccent:  '#FED7AA',
  surface:        '#FFF7ED',   // orange-50

  // ── 방향 ─────────────────────────────────────────────────
  up:             '#EF4444',
  down:           '#22C55E',
  neutral:        '#9CA3AF',
  upLight:        '#FEE2E2',
  downLight:      '#DCFCE7',

  // ── 태그 ─────────────────────────────────────────────────
  tagUpBg:        '#FEE2E2',
  tagUpText:      '#B91C1C',
  tagDownBg:      '#DCFCE7',
  tagDownText:    '#15803D',

  // ── 강도 점 ──────────────────────────────────────────────
  dotHigh:        '#EF4444',
  dotMed:         '#F59E0B',
  dotLow:         '#E5E7EB',

  // ── 신뢰도 ───────────────────────────────────────────────
  highBg:         '#FFF7ED',
  highText:       '#EA580C',
  medBg:          '#FFFBEB',
  medText:        '#92400E',
  lowBg:          '#F9FAFB',
  lowText:        '#6B7280',

  // ── 배경 / 레이아웃 ───────────────────────────────────────
  screenBg:       '#FFFBF7',
  white:          '#FFFFFF',
  border:         '#F3F4F6',
  borderHalf:     '#F3F4F6',

  // ── 헤더 (흰색 + 테두리) ─────────────────────────────────
  headerBg:       '#FFFFFF',
  headerBorder:   '#F3F4F6',
  headerText:     '#111827',   // 흰 배경이므로 검정으로 변경
  headerMuted:    '#6B7280',
  headerAccent:   '#F97316',

  // ── 탭 ───────────────────────────────────────────────────
  tabActive:      '#F97316',
  tabInactive:    '#9CA3AF',

  // ── 텍스트 ───────────────────────────────────────────────
  textPrimary:    '#111827',
  textMuted:      '#6B7280',
  textLight:      '#9CA3AF',
};
```

---

## 3. 파일별 변경 사항 (하드코딩 포함 전수 기재)

### 3-1. `src/constants/category.js`

색상값만 교체. "글로벌 불안지수" 문구는 이 파일에 없으므로 여기서 수정하지 않는다.

```js
// DIRECTION_MAP
up:      { color: '#EF4444', dotColor: '#EF4444' }
down:    { color: '#22C55E', dotColor: '#22C55E' }
neutral: { color: '#9CA3AF', dotColor: '#9CA3AF' }

// MAGNITUDE_MAP
high:   { dots: ['#EF4444', '#EF4444', '#EF4444'] }
medium: { dots: ['#F59E0B', '#F59E0B', '#E5E7EB'] }

// getReliabilityBadge
r >= 0.8 → bg: '#FFF7ED', color: '#EA580C'
r >= 0.5 → bg: '#FFFBEB', color: '#92400E'
r >= 0.3 → bg: '#F9FAFB', color: '#6B7280'
```

---

### 3-2. `src/screens/DashboardScreen.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `StatusBar backgroundColor` | `COLORS.headerBg` | `COLORS.headerBg` (토큰→흰색) |
| `changeColor` 계산 (line ~33) | `'#FF8A7A'` / `'#6EE7B7'` | `COLORS.up` / `COLORS.down` |
| `gaugeBarColor` 4단계 계산 (line ~47–50) | 파랑/노랑/주황/빨강 | `COLORS.primaryAccent` 단색 |
| 인라인 desc `rgba(255,255,255,0.4)` (line ~62) | 반투명 흰색 | `COLORS.textLight` |
| `riskCard.backgroundColor` | `rgba(255,255,255,0.10)` | `COLORS.white` |
| `riskLabel.color` | `rgba(255,255,255,0.9)` | `COLORS.textMuted` |
| `riskBar.backgroundColor` | `rgba(255,255,255,0.15)` | `COLORS.border` |
| `riskBarFill.backgroundColor` | `rgba(255,255,255,0.4)` | `COLORS.primaryAccent` |
| `riskDate.color` | `rgba(255,255,255,0.55)` | `COLORS.textLight` |
| `ActivityIndicator color` | `COLORS.headerBg` | `COLORS.primary` |
| `RefreshControl tintColor/colors` | `COLORS.headerBg` | `COLORS.primary` |
| `RISK_ITEMS[0].label` (line 237) | `'글로벌 위기 지수'` | `'글로벌 불안지수'` |
| `RISK_ITEMS[0].desc` (line 237) | `'지정학적 위기 지수'` | `'글로벌 불안지수'` |
| bottomsheet 본문 (line ~371) | `'본 글로벌 위기 지수는'` | `'본 글로벌 불안지수는'` |

---

### 3-3. `src/screens/NewsListScreen.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `searchBar.backgroundColor` | `rgba(255,255,255,0.12)` | `#F9FAFB` |
| `chip.borderColor` | `rgba(255,255,255,0.2)` | `COLORS.border` |
| `chipText.color` | `rgba(255,255,255,0.65)` | `COLORS.textMuted` |
| `chipTextActive.color` | `COLORS.headerBg` | `COLORS.primary` |
| `ActivityIndicator color` (3곳) | `COLORS.headerBg` | `COLORS.primary` |
| `RefreshControl tintColor/colors` | `COLORS.headerBg` | `COLORS.primary` |

---

### 3-4. `src/screens/RiskScreen.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `tabBtn.borderColor` | `rgba(255,255,255,0.2)` | `COLORS.border` |
| `tabBtnText.color` | `rgba(255,255,255,0.65)` | `COLORS.textMuted` |
| `tabBtnTextActive.color` | `COLORS.headerBg` | `COLORS.primary` |
| `controlDivider.backgroundColor` | `rgba(255,255,255,0.25)` | `COLORS.border` |
| `rangeChip.borderColor` | `rgba(255,255,255,0.15)` | `COLORS.border` |
| `rangeChipActive.borderColor` | `rgba(255,255,255,0.5)` | `COLORS.primary` |
| `rangeChipActive.backgroundColor` | `rgba(255,255,255,0.1)` | `COLORS.surface` |
| `rangeChipText.color` | `rgba(255,255,255,0.5)` | `COLORS.textMuted` |
| `rangeChipTextActive.color` | `rgba(255,255,255,1)` | `COLORS.primary` |
| `modalBtnApply.backgroundColor` | `COLORS.headerBg` | `COLORS.primary` |
| `fsHeader.backgroundColor` | `COLORS.headerBg` | `COLORS.primary` |
| `fsCloseBtn.backgroundColor` | `rgba(255,255,255,0.2)` | `rgba(0,0,0,0.1)` |
| `ActivityIndicator color` | `COLORS.headerBg` | `COLORS.primary` |
| `RefreshControl tintColor/colors` | `COLORS.headerBg` | `COLORS.primary` |
| `ALL_SERIES` 차트 색상 | 하드코딩 다색 | **유지** (데이터 시리즈 구분용) |
| `ALL_SERIES.gpr[0].label` (line 37) | `'글로벌 위기 지수'` | `'글로벌 불안지수'` |

---

### 3-5. `src/screens/SettingsScreen.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `loadingBox.backgroundColor` | `'#EFF6FF'` | `COLORS.surface` |
| `loadingBox.borderColor` | `'#BFDBFE'` | `COLORS.primaryAccent` |
| `loginButton.backgroundColor` | `COLORS.headerBg` | `COLORS.primary` |
| `profileAvatar.backgroundColor` | `COLORS.headerBg` | `COLORS.primary` |
| `Switch trackColor.true` (line 348) | `COLORS.headerBg` | `COLORS.primary` |
| `ActivityIndicator color` | `COLORS.headerBg` | `COLORS.primary` |

---

### 3-6. `src/screens/PredictionListScreen.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `chip.borderColor` | `rgba(255,255,255,0.2)` | `COLORS.border` |
| `chipText.color` | `rgba(255,255,255,0.65)` | `COLORS.textMuted` |
| `chipTextActive.color` | `COLORS.headerBg` | `COLORS.primary` |
| `ActivityIndicator color` | `COLORS.headerBg` | `COLORS.primary` |
| `RefreshControl tintColor/colors` | `COLORS.headerBg` | `COLORS.primary` |

---

### 3-7. `src/components/LoadingView.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `ActivityIndicator color` | `COLORS.primary ?? '#1E3A5F'` | `COLORS.primary` (fallback 제거) |
| `retryBtn.backgroundColor` | `'#1E3A5F'` | `COLORS.primary` |

---

### 3-8. `src/components/FilterChips.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `chipActive.backgroundColor` | `'#1E3A5F'` | `COLORS.primary` |
| `chipActive.borderColor` | `'#1E3A5F'` | `COLORS.primary` |

> **import 추가 필요**: `import { COLORS } from '../constants/colors';`

---

### 3-9. `src/components/PredictionCard.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `predPreviewTag.color` | `COLORS.headerBg` | `COLORS.primary` |

---

### 3-10. `src/components/NewsDetailView.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `StatusBar barStyle` | `light-content` | `dark-content` |
| `header.backgroundColor` | `COLORS.headerBg` | 토큰 교체로 자동 흰색 |
| 헤더 내 텍스트 `rgba(255,255,255,0.8)` (line 157) | 반투명 흰색 | `COLORS.textPrimary` |

---

### 3-11. `src/components/PredictionDetailView.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `header.backgroundColor` | `COLORS.headerBg` | 토큰 교체로 자동 흰색 |
| `backText.color` (line 199) | `rgba(255,255,255,0.7)` | `COLORS.textPrimary` |
| `newsCard.borderLeftColor` | `COLORS.headerBg` | `COLORS.primary` |
| `newsSource.color` | `COLORS.headerBg` | `COLORS.primary` |
| `linkText.color` | `COLORS.headerBg` | `COLORS.primary` |

---

### 3-12. `src/App.jsx`

| 위치 | 현재 | 변경 후 |
|------|------|---------|
| `ActivityIndicator color` | `COLORS.headerBg` | `COLORS.primary` |

---

## 4. 구현 순서

```
1단계 — 토큰 교체
  └── colors.js 전체 교체 (primary 토큰 추가, headerBg→흰색, headerText→검정)
  └── category.js 색상값·용어 교체

2단계 — 인라인 하드코딩 교체 (헤더 흰색 전환 후 보이지 않는 색상 우선)
  └── DashboardScreen: rgba 인라인 → 토큰, changeColor·gaugeBarColor 교체
  └── NewsListScreen: rgba 인라인 → 토큰
  └── RiskScreen: rgba 인라인 → 토큰, tabBtn·rangeChip·fsCloseBtn
  └── PredictionListScreen: rgba 인라인 → 토큰
  └── NewsDetailView: 헤더 내 rgba 텍스트
  └── PredictionDetailView: backText rgba

3단계 — 전경색 COLORS.headerBg → COLORS.primary
  └── DashboardScreen, NewsListScreen, RiskScreen, SettingsScreen, PredictionListScreen,
      App.jsx: ActivityIndicator·RefreshControl
  └── SettingsScreen: loginButton, profileAvatar, Switch
  └── LoadingView: primary 토큰 fallback 제거, retryBtn
  └── FilterChips: chipActive (import 추가)
  └── PredictionCard: predPreviewTag
  └── PredictionDetailView: newsCard·newsSource·linkText

4단계 — 용어 통일 (섹션 8 참고)
  └── DashboardScreen.jsx: RISK_ITEMS[0].label·desc, bottomsheet 본문
  └── RiskScreen.jsx: ALL_SERIES.gpr[0].label

5단계 — 폰트 적용 (선택)
  └── npx expo install @expo-google-fonts/plus-jakarta-sans @expo-google-fonts/dm-mono expo-font
  └── App.jsx useFonts 훅 추가
  └── 주요 컴포넌트 fontFamily 적용
```

---

## 5. 검증 체크리스트

### 5-1. 색상 QA

| 항목 | 확인 위치 | 기대값 |
|------|-----------|--------|
| 헤더 흰색 + 검정 텍스트 | 모든 스크린 상단 | `#FFFFFF` bg, `#111827` text |
| StatusBar 검정 아이콘 | 모든 스크린 (iOS) | `dark-content` |
| 탭 활성 오렌지 | 바텀탭, 내부 탭 칩 | `#F97316` |
| 스피너 오렌지 | 로딩 시 | `#F97316` |
| 버튼 오렌지 | 로그인버튼, 필터적용버튼 | `#F97316` |
| 칩 활성 오렌지 | FilterChips, NewsListScreen, RiskScreen | `#F97316` |
| 상승 빨강, 하락 초록 | DirectionDot, 태그, 카드 | `#EF4444` / `#22C55E` |
| 화면 배경 크림 | 모든 스크린 root | `#FFFBF7` |
| 차트 시리즈 색상 불변 | RiskScreen ALL_SERIES | 변경 없음 |

### 5-2. 기능 QA

| 항목 | 확인 방법 |
|------|-----------|
| 폰트 로딩 에러 없음 | `expo start` 후 console 확인 |
| 헤더 텍스트 가시성 | 각 스크린 헤더 타이틀이 보이는지 확인 |
| DashboardScreen riskCard 가시성 | 카드 라벨·값·바가 보이는지 확인 |
| RiskScreen 풀스크린 닫기 버튼 | fsCloseBtn이 오렌지 배경에서 보이는지 |
| SettingsScreen 로딩박스 | 오렌지 계열 bg로 표시되는지 |
| 글로벌 불안지수 레이블 | RiskScreen 지정학 탭 범례 확인 |
| `npm run lint` 통과 | `front_app/` 에서 실행 |

---

## 6. 변경 대상 파일 목록

**수정 대상 (총 13개)**
```
front_app/src/constants/colors.js               ← 전체 교체 (primary 토큰 추가)
front_app/src/constants/category.js             ← 색상값만 (용어 없음, 색상 교체만)

front_app/src/screens/DashboardScreen.jsx        ← rgba 인라인 + changeColor + gaugeBarColor + 용어 3곳
front_app/src/screens/NewsListScreen.jsx         ← rgba 인라인 + chipTextActive
front_app/src/screens/RiskScreen.jsx             ← rgba 인라인 + tabBtn/rangeChip + 용어 1곳
front_app/src/screens/SettingsScreen.jsx         ← loginButton + profileAvatar + loadingBox + Switch
front_app/src/screens/PredictionListScreen.jsx   ← rgba 인라인 + chipTextActive

front_app/src/components/LoadingView.jsx         ← retryBtn + fallback 제거
front_app/src/components/FilterChips.jsx         ← chipActive (#1E3A5F → primary, import 추가)
front_app/src/components/PredictionCard.jsx      ← predPreviewTag.color
front_app/src/components/NewsDetailView.jsx      ← 헤더 내 rgba 텍스트
front_app/src/components/PredictionDetailView.jsx ← backText + newsCard + newsSource + linkText

front_app/src/App.jsx                            ← ActivityIndicator + 폰트 (5단계)
```

**검토했으나 수정 불필요한 파일**
```
front_app/src/lib/helpers.js                     ← ai_gpr 관련 설명 텍스트만 존재,
                                                    '글로벌 위기 지수' 레이블 없음 → 수정 불필요
front_app/src/lib/supabase.js                    ← DB 쿼리·키 매핑만, UI 레이블 없음 → 수정 불필요
```

**검색/수정 대상에서 제외**
```
dist/, build/, .expo/                            ← 빌드 산출물
docs/, *.md                                      ← 문서 파일 (이 사양서 포함)
front_web/                                       ← 기준 앱, 수정 대상 아님
backend/, prd/, data_collector/                  ← 비프론트 모듈
```

---

## 7. 용어 통일 — 글로벌 불안지수

**확정 용어**: `글로벌 불안지수` (front_web `IndicatorPage.tsx`, `DashboardPage.tsx` 기준)

`category.js`에는 해당 레이블이 없다. 실제 수정 위치는 아래 3곳이다.

| 파일 | 라인 | 현재 문자열 | 교체 문자열 |
|------|------|------------|------------|
| `src/screens/DashboardScreen.jsx` | 237 | `label: '글로벌 위기 지수'` | `label: '글로벌 불안지수'` |
| `src/screens/DashboardScreen.jsx` | 237 | `desc: '지정학적 위기 지수'` | `desc: '글로벌 불안지수'` |
| `src/screens/DashboardScreen.jsx` | ~371 | `'본 글로벌 위기 지수는'` | `'본 글로벌 불안지수는'` |
| `src/screens/RiskScreen.jsx` | 37 | `label: '글로벌 위기 지수'` | `label: '글로벌 불안지수'` |

**검토 결과 수정 불필요**:
- `helpers.js`: `ai_gpr` switch 케이스에 레이블 문자열 없음 (설명 텍스트만 존재)
- `category.js`: `ai_gpr_index` 관련 문자열 없음

---

## 8. 변경하지 않는 것

| 항목 | 이유 |
|------|------|
| `RiskScreen ALL_SERIES` 차트 시리즈 색상 | 지표별 데이터 구분 팔레트, 디자인 통일 대상 아님 |
| Error box (`#FEF2F2`, `#991B1B` 등) | 에러 상태 시맨틱 색상, 유지 |
| `PredictionDetailView` 섹션 박스 (impact·reason·lead·buffer) | 기능별 시맨틱 색상 팔레트, 유지 |
| `InsightCard` 퍼플 (`#4F46E5`, `#7C3AED`) | 독립 기능 색상, 유지 |
| 레이아웃 구조 (바텀 탭, 바텀 시트, 스크롤 방식) | 모바일 UX 최적화 상태 유지 |
| 카드 모서리 반경 (14px) | 모바일 터치 UX 유지 |
| 섀도 스타일 (`elevation`, `shadowOpacity`) | 플랫폼 네이티브 스타일 유지 |
