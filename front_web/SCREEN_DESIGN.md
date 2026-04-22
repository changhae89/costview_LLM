# Costview Web Admin — 화면 설계서 v2

> **작성일**: 2026-04-22 (v2 검토 반영)
> **대상**: `front_web/` 신규 웹 어드민
> **참조**: `front/` (Expo 앱), `backend/` (FastAPI), Supabase DB

---

## 검토 반영 사항

### v1 → v2
| # | 지적 사항 | 반영 내용 |
|---|---|---|
| 1 | 인증/권한 설계 없음 | §3 인증 설계 신규 추가 |
| 2 | RLS/API 책임 경계 불명확 | §4 데이터 접근 책임 경계 명시 |
| 3 | 설계 API ≠ 실제 backend | §4.3 backend 현황 및 구현 필요 목록 명시 |
| 4 | 색상·카테고리 기존 front와 불일치 | §5 토큰 전면 수정 (front 소스 기준) |
| 5 | 대용량 테이블 페이지네이션 기준 없음 | §6 테이블별 페이지네이션 전략 명시 |

### v2 → v3
| # | 분류 | 지적 사항 | 반영 내용 |
|---|---|---|---|
| C1 | Critical | `user_metadata.role` 권한 우회 가능 | `app_metadata.role` 로 변경 |
| C2 | Critical | `jsonb_array_length()` Supabase 클라이언트 불가 | 클라이언트 `.length` 계산으로 수정 |
| C3 | Critical | RLS 활성화 여부 미확인 | 선행 작업 명시 및 확인 절차 추가 |
| M1 | 중간 | JWT 만료 처리 미언급 | 만료·갱신 전략 추가 |
| M2 | 중간 | role 미부여 사용자 처리 미정의 | 기본 정책 명시 |
| M3 | 중간 | 필터 변경 시 page 리셋 미명시 | §6 패턴 코드에 추가 |

---

## 1. 프로젝트 개요

### 1.1 목적

| | 모바일 앱 (`front/`) | 웹 어드민 (`front_web/`) |
|---|---|---|
| 대상 | 일반 소비자 | 운영자 / 분석가 |
| 인증 | 더미 이메일 (AsyncStorage) | Supabase Auth (이메일+비밀번호) |
| 쓰기 | 없음 | 카테고리·품목 CRUD |
| 차트 | 간단 게이지 | 풀 시계열 차트 |

### 1.2 DB 테이블별 건수 (2026-04-22 기준)

| 테이블 | 건수 | 분류 |
|---|---|---|
| `raw_news` | **9,839** | 대용량 — 서버 페이지네이션 필수 |
| `indicator_ecos_daily_logs` | **17,410** | 대용량 — 차트 전용, 테이블 뷰 금지 |
| `indicator_fred_daily_logs` | 3,122 | 중간 — 차트 전용 |
| `indicator_gpr_daily_logs` | 1,186 | 중간 |
| `causal_chains` | 1,212 | 중간 — 서버 페이지네이션 |
| `news_analyses` | 831 | 소형 |
| `indicator_gpr_monthly_logs` | 795 | 소형 |
| `indicator_ecos_monthly_logs` | 735 | 소형 |
| `indicator_kosis_monthly_logs` | 495 | 소형 |
| `cost_categories` | 11 | 소형 — 전체 로드 가능 |
| `consumer_items` | 소량 | 소형 |
| `indicator_fred_monthly_logs` | 147 | 소형 |

---

## 2. 기술 스택

```
front_web/
├── Vite + React 18 + TypeScript
├── Tailwind CSS v3
├── shadcn/ui  (Radix UI 기반)
├── React Router v6
├── @supabase/supabase-js  (읽기 전용 — anon key)
├── Recharts  (시계열 차트)
├── TanStack Table v8  (데이터 그리드)
└── TanStack Query v5  (서버 상태 캐시)
```

---

## 3. 인증 / 권한 설계

### 3.1 인증 방식

**Supabase Auth (이메일 + 비밀번호)**

```
로그인 흐름:
  사용자 입력 (email/password)
    → supabase.auth.signInWithPassword()
    → Supabase JWT 발급 (access_token + refresh_token)
    → localStorage 저장 (Supabase SDK 자동 처리)
    → 보호 라우트 접근 허용
```

**[M1] JWT 만료 처리**:
- access_token 기본 만료: 1시간
- Supabase SDK의 `autoRefreshToken: true` (기본값) 로 자동 갱신
- 갱신 실패(네트워크 오류, refresh_token 만료) 시: `supabase.auth.onAuthStateChange` 이벤트 `SIGNED_OUT` 수신 → `/login` 리디렉트
- FastAPI 호출 시 401 응답 → SDK로 `refreshSession()` 재시도 1회 → 실패 시 로그아웃

```ts
// lib/api.ts — FastAPI 호출 래퍼
async function apiFetch(url: string, options: RequestInit) {
  const { data: { session } } = await supabase.auth.getSession()
  const res = await fetch(url, {
    ...options,
    headers: { Authorization: `Bearer ${session?.access_token}`, ...options.headers },
  })
  if (res.status === 401) {
    await supabase.auth.refreshSession()
    // 재시도 1회
    const { data: { session: next } } = await supabase.auth.getSession()
    if (!next) { /* 로그아웃 처리 */ throw new Error('session_expired') }
    return fetch(url, { ...options, headers: { Authorization: `Bearer ${next.access_token}` } })
  }
  return res
}
```

### 3.2 역할 정의

| 역할 | Supabase 메타데이터 | 접근 범위 |
|---|---|---|
| `admin` | `app_metadata.role = "admin"` | 모든 화면 + CRUD |
| `viewer` | `app_metadata.role = "viewer"` | 읽기 전용 화면만 |
| (미부여) | `app_metadata.role` 없음 | viewer와 동일하게 처리 |

> **[C1 수정]** `user_metadata`는 사용자가 클라이언트에서 직접 수정 가능 → 권한 우회 가능.
> `app_metadata`는 service role 또는 Supabase 대시보드에서만 수정 가능하므로 반드시 `app_metadata.role` 사용.

- 역할은 Supabase 대시보드 → Authentication → Users → Edit user → `app_metadata` 에서 수동 부여
- 프론트에서 `user.app_metadata?.role` 확인 후 쓰기 버튼 렌더링 여부 결정
- **[M2 수정]** `role`이 없는 신규 사용자는 기본값 `viewer`로 취급 (코드: `role ?? 'viewer'`)

### 3.3 라우트 보호

```tsx
// app/router.tsx
<Route element={<RequireAuth />}>          {/* 로그인 필수 */}
  <Route path="/" element={<DashboardPage />} />
  <Route path="/news" element={<NewsPage />} />
  <Route path="/causal" element={<CausalPage />} />
  <Route path="/indicators" element={<IndicatorPage />} />
  <Route element={<RequireAdmin />}>       {/* app_metadata.role === "admin" 필수 */}
    <Route path="/settings/categories" element={<CategoryPage />} />
    <Route path="/settings/consumer-items" element={<ConsumerItemPage />} />
  </Route>
</Route>
<Route path="/login" element={<LoginPage />} />
```

```ts
// hooks/useAuth.ts  — 역할 판별 헬퍼
export function useRole() {
  const { data: { user } } = useSupabaseUser()
  const role = user?.app_metadata?.role ?? 'viewer'  // [M2] 미부여 시 viewer
  return { role, isAdmin: role === 'admin' }
}
```

### 3.4 로그인 화면 스펙 (SCR-W00)

```
경로: /login  (미인증 시 리디렉트)

┌──────────────────────────────┐
│        [로고]                │
│    Costview Admin            │
│                              │
│  이메일  [________________]  │
│  비밀번호 [________________]  │
│                              │
│       [로그인]               │
│                              │
│  ※ 계정 발급: 관리자 문의    │
└──────────────────────────────┘

에러 처리:
- 인증 실패 → "이메일 또는 비밀번호가 올바르지 않습니다."
- 권한 없음 → "접근 권한이 없습니다. 관리자에게 문의하세요."
```

---

## 4. 데이터 접근 책임 경계

### 4.1 원칙

```
읽기 (SELECT)  → Supabase 클라이언트 직접 (anon key + RLS)
쓰기 (INSERT/UPDATE/DELETE) → FastAPI 경유 (service role key 서버 보관)
```

- anon key는 프론트에 노출돼도 안전 (RLS가 SELECT만 허용)
- service role key는 절대 프론트에 노출 금지 → FastAPI에서만 사용

### 4.2 RLS 정책 요구사항

> **[C3 선행 작업]** 구현 전 반드시 확인:
> Supabase 대시보드 → Table Editor → 각 테이블 → RLS 탭에서 **"Enable RLS" 활성화** 여부 확인.
> RLS 비활성 상태에서는 anon key로 모든 쓰기가 가능하므로 **RLS 활성화가 먼저**다.

| 테이블 | RLS 활성화 | anon SELECT | 인증 INSERT/UPDATE/DELETE |
|---|---|---|---|
| `cost_categories` | 확인 필요 | ✓ (전체) | ✗ (FastAPI service role만) |
| `consumer_items` | 확인 필요 | ✓ (`is_deleted=false`) | ✗ (FastAPI service role만) |
| `raw_news` | 확인 필요 | ✓ (`is_deleted=false`) | ✗ |
| `news_analyses` | 확인 필요 | ✓ | ✗ |
| `causal_chains` | 확인 필요 | ✓ | ✗ |
| `indicator_*` | 확인 필요 | ✓ | ✗ |

적용할 RLS 정책 예시:
```sql
-- cost_categories: anon 읽기 허용
CREATE POLICY "anon read" ON cost_categories
  FOR SELECT TO anon USING (true);

-- consumer_items: 삭제되지 않은 항목만 anon 읽기
CREATE POLICY "anon read active" ON consumer_items
  FOR SELECT TO anon USING (is_deleted = false);
```

### 4.3 FastAPI backend 현황 및 구현 필요 목록

**현재 구현된 엔드포인트** (`backend/`):

| 엔드포인트 | 상태 | 비고 |
|---|---|---|
| `GET /api/v1/categories` | 하드코딩 목록 반환 | DB 미연결 |
| `GET /api/news` | 뼈대만 | 미구현 |
| `GET /api/indicators/latest` | 뼈대만 | 미구현 |

**웹 어드민을 위해 신규 구현 필요**:

| 엔드포인트 | 용도 | 우선순위 |
|---|---|---|
| `POST /api/v1/categories` | 카테고리 추가 | 높음 |
| `PUT /api/v1/categories/{code}` | 카테고리 수정 | 높음 |
| `DELETE /api/v1/categories/{code}` | 카테고리 삭제 | 높음 |
| `POST /api/v1/consumer-items` | 품목 추가 | 높음 |
| `PUT /api/v1/consumer-items/{id}` | 품목 수정 | 높음 |
| `DELETE /api/v1/consumer-items/{id}` | 소프트 삭제 | 높음 |
| `POST /api/v1/consumer-items/{id}/restore` | 소프트 삭제 복구 | 중간 |

**FastAPI 인증 방식**:
```
프론트 → Authorization: Bearer <Supabase JWT>
FastAPI → supabase.auth.get_user(token) 검증
        → user_metadata.role == "admin" 확인
        → 통과 시 service role key로 DB 쓰기
```

**FastAPI 응답 포맷** (통일):
```json
{ "data": {...}, "error": null }
{ "data": null,  "error": "message" }
```

---

## 5. 색상 / 카테고리 상수 (front 소스 기준 통일)

> `front/src/constants/colors.js` 및 `category.js` 를 그대로 TypeScript로 포팅

### 5.1 색상 토큰

| 토큰 | 값 | 용도 |
|---|---|---|
| `primary` | `#0D9488` | 헤더, 사이드바 활성, 버튼 (← v1의 `#1B3A5C` 오류 수정) |
| `primaryAccent` | `#5EEAD4` | 헤더 서브텍스트 |
| `up` | `#D85A30` | 상승 (← v1의 `#EF4444` 오류 수정) |
| `down` | `#1D9E75` | 하락 (← v1의 `#22C55E` 오류 수정) |
| `neutral` | `#B4B2A9` | 중립 (← v1의 `#9CA3AF` 오류 수정) |
| `upLight` | `#FF8A7A` | 상승 연한 배경용 |
| `downLight` | `#6EE7B7` | 하락 연한 배경용 |
| `tagUpBg` | `#FCEBEB` | 상승 태그 배경 |
| `tagUpText` | `#791F1F` | 상승 태그 텍스트 |
| `tagDownBg` | `#EAF3DE` | 하락 태그 배경 |
| `tagDownText` | `#27500A` | 하락 태그 텍스트 |
| `dotHigh` | `#D85A30` | 강도 High 점 |
| `dotMed` | `#EF9F27` | 강도 Medium 점 |
| `dotLow` | `#E5E7EB` | 강도 Low 점 |
| `surface` | `#F4F7FA` | 페이지 배경 |
| `border` | `#E5E7EB` | 구분선 |
| `textPrimary` | `#111827` | 본문 텍스트 |
| `textMuted` | `#6B7280` | 보조 텍스트 |

### 5.2 카테고리 매핑 (DB 코드 → 한글)

```ts
// front/src/constants/category.js 그대로 포팅
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
};

export const DIRECTION_MAP = {
  up:      { label: '▲ 상승', color: '#D85A30' },
  down:    { label: '▼ 하락', color: '#1D9E75' },
  neutral: { label: '─ 중립', color: '#111827' },
};

export const MAGNITUDE_MAP = {
  high:   { label: '강함', dots: ['#D85A30','#D85A30','#D85A30'] },
  medium: { label: '보통', dots: ['#EF9F27','#EF9F27','#E5E7EB'] },
  low:    { label: '약함', dots: ['#E5E7EB','#E5E7EB','#E5E7EB'] },
};
```

---

## 6. 페이지네이션 전략

| 테이블 | 건수 | 전략 | 기준 |
|---|---|---|---|
| `raw_news` | 9,839 | **서버 페이지네이션** | 50건/페이지, Supabase `.range(from, to)` |
| `causal_chains` | 1,212 | **서버 페이지네이션** | 50건/페이지 |
| `news_analyses` | 831 | **서버 페이지네이션** | 50건/페이지 |
| `indicator_ecos_daily_logs` | 17,410 | **차트 전용** (테이블 뷰 금지), 기간 필터 필수 |
| `indicator_fred_daily_logs` | 3,122 | **차트 전용**, 기간 필터 필수 |
| `indicator_gpr_daily_logs` | 1,186 | 차트 전용, limit 1,250 (앱과 동일) |
| `indicator_*_monthly_logs` | 147~795 | 전체 로드 후 클라이언트 렌더 |
| `cost_categories` | 11 | 전체 로드 (페이지네이션 불필요) |
| `consumer_items` | 소량 | 전체 로드 |

**서버 페이지네이션 공통 패턴**:
```ts
const PAGE_SIZE = 50;

// [M3] 필터 변경 시 반드시 page를 0으로 리셋
function useTableData(filters: Filters) {
  const [page, setPage] = useState(0)

  useEffect(() => {
    setPage(0)          // 필터 바뀌면 첫 페이지로
  }, [filters])

  const query = useQuery({
    queryKey: ['raw_news', filters, page],
    queryFn: async () => {
      const { data, count } = await supabase
        .from('raw_news')
        .select('*', { count: 'estimated' })   // exact 대신 estimated (성능)
        .match(filters)
        .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)
        .order('created_at', { ascending: false })
      return { data, total: count ?? 0 }
    },
  })
  return { ...query, page, setPage, totalPages: Math.ceil((query.data?.total ?? 0) / PAGE_SIZE) }
}
```

> `count: 'estimated'` — PostgreSQL 통계 기반 추정치. 9,839건 규모에서 `exact` 대비 쿼리 1개 절감. 총 페이지 수 표시에 실용적으로 충분.

**indicator 차트 기간 필터 기본값**:
- 기본: 최근 1년 (`reference_date >= now() - interval '1 year'`)
- 선택: 1M / 3M / 6M / 1Y / ALL (ALL 선택 시 경고 표시)

---

## 7. 디자인 시스템

> **적용 스킬**: `frontend-design` + `theme-factory / Ocean Depths` (적응 적용)
> Ocean Depths의 깊은 해양 팔레트를 기존 민트 브랜드(`#0D9488`)와 결합. 어드민 툴에 걸맞는 **Refined Utilitarian** 방향으로 확정.

### 7.1 디자인 방향 (frontend-design 기준)

| 항목 | 결정 | 근거 |
|---|---|---|
| **톤** | Refined Utilitarian — 정보 밀도 높되 군더더기 없음 | 운영자가 하루 수십 번 쓰는 툴, 피로감 최소화 |
| **차별점** | 민트+딥네이비 2-tone 사이드바, 데이터 셀에 모노스페이스 적용 | 숫자/코드가 많은 어드민에서 가독성 극대화 |
| **금지** | Inter, Roboto, Arial, Space Grotesk, 보라 그라디언트 | frontend-design 스킬 금지 목록 |

### 7.2 타이포그래피

> `frontend-design`: "Avoid generic fonts. Pair a distinctive display font with a refined body font."

```css
/* Google Fonts — 빌드 시 로드 */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
```

| 역할 | 폰트 | 용도 |
|---|---|---|
| **Display / Heading** | `Plus Jakarta Sans` 700 | 페이지 제목, 섹션 헤더 |
| **Body** | `Plus Jakarta Sans` 400·500 | 본문, 레이블, 버튼 |
| **Data / Mono** | `DM Mono` 400·500 | 숫자, 코드, ID, 날짜, 퍼센트 값 |

```css
:root {
  --font-display: 'Plus Jakarta Sans', sans-serif;
  --font-mono: 'DM Mono', monospace;
}

/* 숫자·ID가 들어가는 테이블 셀은 반드시 모노 */
.cell-number, .cell-id, .cell-date, .cell-percent {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
```

### 7.3 색상 시스템 (Ocean Depths × 브랜드 확장)

> `theme-factory / Ocean Depths` 기반 — 기존 앱 브랜드 컬러(`#0D9488`) 우선 유지, Navy 계열로 보완

```css
:root {
  /* ── 브랜드 (기존 front/ 앱 계승) ── */
  --color-primary:        #0D9488;   /* 헤더, 활성 메뉴, 주요 버튼 */
  --color-primary-accent: #5EEAD4;   /* 호버, 하이라이트 */

  /* ── Ocean Depths 확장 ── */
  --color-navy:           #1A2332;   /* 사이드바 배경 */
  --color-navy-light:     #243044;   /* 사이드바 호버 */
  --color-seafoam:        #A8DADC;   /* 보조 강조 (뱃지, 링크) */

  /* ── 방향 신호 (front/ 앱 그대로) ── */
  --color-up:             #D85A30;
  --color-down:           #1D9E75;
  --color-neutral:        #B4B2A9;

  /* ── 표면 ── */
  --color-surface:        #F4F7FA;   /* 페이지 배경 */
  --color-card:           #FFFFFF;
  --color-border:         #E5E7EB;

  /* ── 텍스트 ── */
  --color-text-primary:   #111827;
  --color-text-muted:     #6B7280;
  --color-text-light:     #9CA3AF;

  /* ── 상태 ── */
  --color-success:        #1D9E75;
  --color-warning:        #EF9F27;
  --color-error:          #D85A30;
  --color-info:           #A8DADC;
}
```

### 7.4 모션 / 마이크로인터랙션

> `frontend-design`: "Focus on high-impact moments. One well-orchestrated page load creates more delight than scattered micro-interactions."

```css
/* 전역 트랜지션 기준 */
:root {
  --duration-fast:   120ms;
  --duration-base:   200ms;
  --duration-slow:   350ms;
  --ease-out:        cubic-bezier(0.16, 1, 0.3, 1);
}
```

| 상황 | 효과 | 구현 |
|---|---|---|
| 페이지 진입 | 콘텐츠 영역 `fadeInUp` stagger (카드 순서대로) | CSS `animation-delay` |
| 사이드바 메뉴 전환 | 좌측 활성 바 `scaleY` 슬라이드 | CSS `transform` |
| Drawer 열기 | 우측에서 `translateX` 슬라이드인 | Motion `animate()` |
| 테이블 행 hover | 배경 `#F4F7FA` → `#EFF6FF` 페이드 | CSS `transition` |
| KPI 카드 숫자 | 0에서 목표값까지 카운트업 | `useCountUp` hook |
| 버튼 클릭 | `scale(0.97)` 누름 효과 | CSS `active:scale` |
| 모달 등장 | `scale(0.95) opacity(0)` → 정상 | Motion `animate()` |

**금지**: 스크롤 패럴렉스, 루프 애니메이션, 화면 전체 로딩 스피너 (Skeleton UI 대체)

### 7.5 공간 구성 (Spatial Composition)

> `frontend-design`: "Controlled density for data-heavy admin tools."

```
스페이싱 스케일 (4px 기준):
  xs: 4px  |  sm: 8px  |  md: 16px  |  lg: 24px  |  xl: 32px  |  2xl: 48px

카드 내부 패딩:     24px (lg)
테이블 행 높이:     48px
섹션 간격:          32px (xl)
사이드바 아이템:    12px 상하, 16px 좌우
```

**레이아웃 특이점**:
- 헤더는 `#0D9488` 단색이 아닌 **미세 노이즈 텍스처 오버레이** 적용 (깊이감)
- 대시보드 KPI 카드는 **좌상단 컬러 액센트 바** (4px, primary 색상)
- 차트 영역 배경은 `#FAFBFC` (카드보다 살짝 어둡게) — 데이터와 UI 구분

### 7.6 컴포넌트 스타일 기준

```tsx
/* KPI 카드 — 액센트 바 + 모노 숫자 */
<div className="relative rounded-xl bg-white shadow-sm border border-gray-100 p-6">
  <div className="absolute top-0 left-0 w-1 h-full rounded-l-xl bg-[#0D9488]" />
  <span className="font-mono text-3xl font-medium tabular-nums">{value}</span>
</div>

/* 테이블 퍼센트 셀 — 방향 색상 + 모노 */
<td className="font-mono tabular-nums text-[#D85A30]">+22.6%</td>

/* 상태 뱃지 */
<span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
  bg-[#EAF3DE] text-[#27500A]">processed</span>
```

**Tailwind 커스텀 설정** (`tailwind.config.ts`):
```ts
theme: {
  extend: {
    fontFamily: {
      sans: ['Plus Jakarta Sans', 'sans-serif'],
      mono: ['DM Mono', 'monospace'],
    },
    colors: {
      primary: '#0D9488',
      navy:    '#1A2332',
      seafoam: '#A8DADC',
    },
  },
}
```

---

## 8. 폴더 구조 (업데이트)

```
front_web/src/
├── app/
│   ├── router.tsx            # 라우트 + 보호 래퍼
│   ├── main.tsx
│   └── hooks/
│       └── useAuth.ts        # useRole() 포함 [C1]
├── pages/
│   ├── LoginPage.tsx         # SCR-W00
│   ├── DashboardPage.tsx     # SCR-W01
│   ├── NewsPage.tsx          # SCR-W02
│   ├── CausalPage.tsx        # SCR-W03
│   ├── IndicatorPage.tsx     # SCR-W04
│   ├── CategoryPage.tsx      # SCR-W05 (admin only)
│   └── ConsumerItemPage.tsx  # SCR-W06 (admin only)
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx       # Navy 사이드바 + 활성 바
│   │   └── Header.tsx        # 민트 헤더 + 노이즈 텍스처
│   ├── charts/
│   │   ├── TimeSeriesChart.tsx
│   │   └── CategoryBarChart.tsx
│   └── ui/                   # shadcn 컴포넌트
├── lib/
│   ├── supabase.ts           # 읽기 전용 쿼리 (anon key)
│   ├── api.ts                # FastAPI 쓰기 래퍼 + JWT 갱신 [M1]
│   └── helpers.ts
├── constants/
│   ├── category.ts           # front/category.js 포팅
│   └── colors.ts             # CSS 변수 기준 (§7.3)
└── styles/
    ├── globals.css            # CSS 변수 + 폰트 import
    └── animations.css         # fadeInUp, scaleY 등 (§7.4)
```

---

## 8. 레이아웃 공통 (디자인 시스템 적용)

```
┌──────────────────────────────────────────────────────┐
│  HEADER (#0D9488 + 노이즈 텍스처)   [날짜] [계정▼]   │
│  height: 56px  |  font: Plus Jakarta Sans 600        │
├────────────┬─────────────────────────────────────────┤
│            │                                         │
│ SIDEBAR    │  PAGE CONTENT                           │
│ (#1A2332)  │  background: #F4F7FA                    │
│ width:240px│                                         │
│            │                                         │
│ [▌대시보드] │  ← 활성: 좌측 4px #5EEAD4 바 + 텍스트 흰색│
│  뉴스관리  │  ← 비활성: 텍스트 #A8DADC (seafoam)      │
│  인과관계  │                                         │
│  지표      │                                         │
│  ───────  │                                         │
│  카테고리  │  ← admin only (viewer에서 렌더 안 함)    │
│  품목      │                                         │
└────────────┴─────────────────────────────────────────┘
```

**헤더 (`Header.tsx`)**:
- 배경: `#0D9488` + `background-image: url(noise.svg)` 5% opacity 오버레이
- 로고 텍스트: `DM Mono` 500, 크기 15px, 대문자
- 우측: 현재 날짜 (`DM Mono`) + 계정 드롭다운 (이름, 로그아웃)

**사이드바 (`Sidebar.tsx`)**:
- 배경: `#1A2332` (Navy)
- 메뉴 아이템: `Plus Jakarta Sans` 500, 14px
  - 활성: 배경 `#243044`, 좌측 4px `#5EEAD4` 바, 텍스트 `#FFFFFF`
  - 비활성: 텍스트 `#A8DADC`, hover 배경 `#243044` transition 120ms
- admin 섹션 구분선: `#2D3E55` 1px

**페이지 콘텐츠**:
- 배경: `#F4F7FA`
- 최상단 페이지 제목: `Plus Jakarta Sans` 700, 22px, `#111827`
- 카드: `background #FFF`, `border-radius 12px`, `box-shadow 0 1px 3px rgba(0,0,0,0.08)`
- 카드 좌상단 강조 바: 4px × 100% height, `#0D9488`
- 진입 애니메이션: 카드 순서대로 `fadeInUp` stagger `animation-delay: 0ms, 60ms, 120ms …`

---

## 9. 화면 상세 설계

---

### SCR-W00 로그인 (Login)

**경로**: `/login`

→ §3.4 참조

---

### SCR-W01 대시보드 (Dashboard)

**경로**: `/`
**권한**: viewer 이상
**데이터 소스**: Supabase 직접 읽기

```
┌──────────────────────────────────────────────────┐
│  KPI 카드 (5개)                                   │
│  [GPR지수] [원/달러] [WTI] [한국CPI] [미10년채]  │
├──────────────────────────────────────────────────┤
│  뉴스 파이프라인 도넛            │ GPR 30일 추이  │
│  ■processed  830                │ (LineChart)    │
│  ■skipped  7,679                │                │
│  ■pending  1,329                │                │
│  ■failed       1                │                │
├──────────────────────────────────────────────────┤
│  카테고리별 인과관계 (상위10)    │ 최근 분석 뉴스 │
│  fuel▲  ████░ 495건             │ (최신 5건)     │
│  food▲  ██░░░ 182건             │                │
│  energy▲ █░░░ 158건             │                │
└──────────────────────────────────────────────────┘
```

**KPI 카드**:

| 지표 | 테이블 | 컬럼 | max |
|---|---|---|---|
| 글로벌 위기 지수 | `indicator_gpr_daily_logs` | `ai_gpr_index` | 300 |
| 원/달러 환율 | `indicator_ecos_daily_logs` | `krw_usd_rate` | 2,000 |
| WTI 원유 | `indicator_fred_daily_logs` | `fred_wti` | 150 |
| 한국 소비자물가 | `indicator_kosis_monthly_logs` | `cpi_total` | 10 |
| 미 10년 국채 | `indicator_fred_daily_logs` | `fred_treasury_10y` | 8 |

카드 내부: `현재값 / 전일대비(▲▼색상) / 날짜 / 게이지바`

---

### SCR-W02 뉴스 관리 (News)

**경로**: `/news`
**권한**: viewer 이상
**데이터 소스**: Supabase 직접 읽기
**페이지네이션**: 서버, 50건/페이지 (`raw_news` 9,839건)

#### 서브탭: [원본 뉴스] [분석 결과]

**2-1. 원본 뉴스** (`raw_news`, 9,839건 → 서버 페이지네이션)

필터바:
- `processing_status` 체크박스 (processed / skipped / pending / failed)
- 키워드 검색 (`title` ilike)
- 날짜 범위 (`origin_published_at`)
- 삭제 항목 포함 토글 (`is_deleted`)

컬럼:

| 컬럼 | 소스 |
|---|---|
| 제목 | `title` (클릭 → `news_url` 새 탭) |
| 처리 상태 | `processing_status` Badge |
| 키워드 | `keyword[]` 태그 |
| 상승 품목 | `increased_items[]` ▲빨강 |
| 하락 품목 | `decreased_items[]` ▼초록 |
| 발행일 | `origin_published_at` |
| 재시도 | `retry_count` |

행 선택 → 우측 Drawer: 연결된 `news_analyses` 요약 표시

**2-2. 분석 결과** (`news_analyses`, 831건 → 서버 페이지네이션 50건)

컬럼: `summary` / `reliability`(바) / `time_horizon` / `geo_scope` / `korea_relevance` / `created_at`

행 클릭 → 모달:
- summary / 신뢰도+이유
- `effect_chain[]` → 흐름 화살표 (`→` 연결)
- 연결된 `causal_chains` 목록

---

### SCR-W03 인과관계 탐색 (Causal Chains)

**경로**: `/causal`
**권한**: viewer 이상
**데이터 소스**: Supabase 직접 읽기
**페이지네이션**: 서버, 50건/페이지 (1,212건)

#### DB 실측 분포

| 항목 | 분포 |
|---|---|
| 카테고리 | fuel 495 / food 182 / energy 158 / gas 96 / shipping 58 / price 55 / commodity 51 / cost 47 / oil 42 / inflation 28 |
| 방향 | up 981 / down 195 / neutral 36 |
| 강도 | high 530 / medium 524 / low 158 |
| raw_shock_percent | min -93% / max +1,000% / avg +22.6% |
| wallet_hit_percent | min -50% / max +367% / avg +5% |
| 전달기간 | 1개월 745 / 3개월 352 / 2개월 82 / 6개월 26 |
| logic_steps | 3단계 592 / 4단계 464 / 5단계 94 |

#### 레이아웃

```
┌──────────────────────────────────────────────────────────┐
│  필터: [카테고리▼] [방향▼] [강도▼] [전달기간▼] [신뢰도≥] │
├──────────────────────────────────────────────────────────┤
│  [카테고리×방향 히트맵]  [충격% 히스토그램]  [전달기간 분포] │
├──────────────────────────────────────────────────────────┤
│  인과관계 테이블 (서버 페이지네이션 50건)                 │
└──────────────────────────────────────────────────────────┘
```

**차트 1 — 카테고리×방향 누적 막대** (Recharts HorizontalBar):
- y: 카테고리(한글), x: 건수, 색상: up=#D85A30 / down=#1D9E75 / neutral=#B4B2A9

**차트 2 — 충격% 히스토그램**:
- 구간: `<-50` / `-50~0` / `0~10` / `10~30` / `30~100` / `>100`
- 양수 막대=#D85A30, 음수 막대=#1D9E75

**차트 3 — 전달기간 분포**:
- 1개월 745 / 2개월 82 / 3개월 352 / 6개월 26 / 24개월 2

**테이블 컬럼**:

| 컬럼 | 소스 | 비고 |
|---|---|---|
| 이벤트 | `event` | 80자 truncate, hover 툴팁 |
| 카테고리 | `category` | CATEGORY_MAP 한글 |
| 방향 | `direction` | ▲/▼/─ 컬러 뱃지 (`DIRECTION_MAP`) |
| 강도 | `magnitude` | ●●● 점 (`MAGNITUDE_MAP`) |
| 원충격% | `raw_shock_percent` | `±N%` 컬러 |
| 지갑영향% | `wallet_hit_percent` | `±N%` 컬러 |
| 전달기간 | `transmission_time_months` | `N개월` |
| 인과단계 | `logic_steps` | `row.logic_steps?.length ?? 0` + `N단계` 표시 [C2] |
| 신뢰도 | `news_analyses.reliability` | 0~1 바 |
| 분석일 | `news_analyses.created_at` | YYYY-MM-DD |

**행 클릭 → 우측 Drawer**:
- 카테고리/방향/강도 뱃지
- 이벤트 / 메커니즘 텍스트
- `logic_steps[]` 단계 흐름 (`1→2→3→4`)
- `raw_shock_factors[]` / `wallet_hit_factors[]` 태그
- 수치 요약: 원충격% / 지갑영향% / 전달기간 / 전달이유
- 연결된 뉴스 분석 카드 (summary + reliability)

---

### SCR-W04 지표 모니터링 (Indicators)

**경로**: `/indicators`
**권한**: viewer 이상
**데이터 소스**: Supabase 직접 읽기
**주의**: `indicator_ecos_daily_logs` 17,410건 — **테이블 뷰 금지, 차트 전용**

#### 서브탭: [일별 지표] [월별 지표]

**기간 선택 (공통)**: 1M / 3M / 6M / 1Y / ALL
- ALL 선택 시 경고: "데이터가 많아 로딩이 느릴 수 있습니다"
- 기본값: 1Y

**4-1. 일별 지표** (Recharts LineChart, x=날짜):

| 차트 그룹 | 시리즈 | 소스 테이블 |
|---|---|---|
| 지정학 위기 | ai_gpr_index, gpr_original, oil_disruptions | `indicator_gpr_daily_logs` |
| 환율·금리 | krw_usd_rate, kr_bond_3y | `indicator_ecos_daily_logs` |
| 에너지 | fred_wti, fred_brent, fred_natural_gas | `indicator_fred_daily_logs` |
| 미국 채권 | fred_treasury_10y, fred_treasury_2y | `indicator_fred_daily_logs` |
| 달러 지수 | fred_usd_index | `indicator_fred_daily_logs` |

**4-2. 월별 지표**:

| 차트 그룹 | 시리즈 | 소스 테이블 |
|---|---|---|
| 한국 소비자물가 | cpi_total, core_cpi, cpi_petroleum | `indicator_kosis_monthly_logs` |
| 수입물가 | import_price_crude_oil, import_price_food, import_price_coal | `indicator_ecos_monthly_logs` |
| 생산자물가 | ppi_total, ppi_food, ppi_energy | `indicator_ecos_monthly_logs` |
| 미국 거시 | fred_cpi, fred_pce, fred_unrate, fred_fedfunds | `indicator_fred_monthly_logs` |
| 곡물 | fred_wheat, fred_corn, fred_soybean | `indicator_fred_monthly_logs` |
| 해운·공급망 | fred_bdi, fred_gepu | `indicator_fred_monthly_logs` |

---

### SCR-W05 카테고리 관리 (Categories)

**경로**: `/settings/categories`
**권한**: **admin 전용**
**데이터 소스**: 읽기=Supabase / 쓰기=FastAPI

```
┌──────────────────────────────────────────────────┐
│  [+ 카테고리 추가]        [그룹▼] [검색]           │
├──────────────────────────────────────────────────┤
│  그룹: energy                                     │
│  ⊙ 기름값(oil)   키워드: oil, crude, …   [수정][삭제]│
│  ⊙ 주유비(fuel)  키워드: fuel, gasoline,… [수정][삭제]│
│  그룹: living  ...                                │
└──────────────────────────────────────────────────┘
```

**추가/수정 모달** (Dialog):

```
코드 *          [____]  (수정 시 읽기 전용)
한글명 *        [________]
영문명          [________]
그룹 *          [energy▼ / living▼ / economy▼ / supply_chain▼]
키워드          [TagInput — space/enter로 추가]
정렬순서        [숫자]
활성화          [토글]
              [취소]  [저장]
```

**API 호출** (FastAPI, JWT 첨부):
- 추가: `POST /api/v1/categories`
- 수정: `PUT /api/v1/categories/{code}`
- 삭제: `DELETE /api/v1/categories/{code}` (확인 Dialog 필수)
- `is_active` 토글: `PUT /api/v1/categories/{code}` 인라인

**[M4] 쓰기 후 UI 갱신 — TanStack Query invalidate**:
```ts
const queryClient = useQueryClient()
const mutation = useMutation({
  mutationFn: (body) => apiFetch('/api/v1/categories', { method: 'POST', body }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['categories'] })  // 목록 자동 재조회
  },
})
```

---

### SCR-W06 품목 관리 (Consumer Items)

**경로**: `/settings/consumer-items`
**권한**: **admin 전용**
**데이터 소스**: 읽기=Supabase / 쓰기=FastAPI

```
┌──────────────────────────────────────────────────┐
│  [+ 품목 추가]    [삭제된 항목 표시 ○]  [검색]    │
├──────────────────────────────────────────────────┤
│  카테고리(KR) | 키워드(KR) | 키워드(EN) | 등록일 | 액션 │
│  소비재        | 전쟁       | war        | 04-08  | [수정][삭제] │
└──────────────────────────────────────────────────┘
```

**추가/수정 모달**:
- 카테고리(KR) * / 카테고리(EN) / 키워드(KR) * / 키워드(EN)

**API 호출** (FastAPI, JWT 첨부):
- 추가: `POST /api/v1/consumer-items`
- 수정: `PUT /api/v1/consumer-items/{id}`
- 삭제: `DELETE /api/v1/consumer-items/{id}` → `is_deleted=true` (소프트 삭제)
- 복구: `POST /api/v1/consumer-items/{id}/restore`

**[M4] 쓰기 후 UI 갱신**:
```ts
onSuccess: () => queryClient.invalidateQueries({ queryKey: ['consumer-items'] })
```

---

## 10. 공통 컴포넌트

| 컴포넌트 | 설명 |
|---|---|
| `RequireAuth` | 미인증 → `/login` 리디렉트 |
| `RequireAdmin` | viewer → 403 페이지 |
| `StatusBadge` | processed/skipped/pending/failed 색상 뱃지 |
| `DirectionBadge` | ▲/▼/─ (DIRECTION_MAP 색상) |
| `MagnitudeDots` | ●●● (MAGNITUDE_MAP 색상) |
| `ReliabilityBar` | 0~1 → 컬러 바 + % 텍스트 |
| `CategoryTag` | code → CATEGORY_MAP 한글 변환 |
| `TimeSeriesChart` | Recharts LineChart 래퍼 + 기간 선택 |
| `DataTable` | TanStack Table + 서버 페이지네이션 |
| `ConfirmDialog` | 삭제 확인 모달 |
| `TagInput` | 키워드 배열 입력 (space/enter 구분) |

---

## 11. 개발 우선순위

| 순위 | 화면/작업 | 의존성 |
|---|---|---|
| 1 | SCR-W00 로그인 + RequireAuth | 없음 |
| 2 | SCR-W01 대시보드 | Supabase 읽기 |
| 3 | SCR-W02 뉴스 관리 | Supabase 읽기 |
| 4 | backend CRUD API 구현 | FastAPI + service role |
| 5 | SCR-W05 카테고리 관리 | backend API |
| 6 | SCR-W06 품목 관리 | backend API |
| 7 | SCR-W03 인과관계 탐색 | Supabase 읽기 |
| 8 | SCR-W04 지표 모니터링 | Supabase 읽기 |
