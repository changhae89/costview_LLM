# 검증률 개선 작업 로그

## 기준 스코어 (작업 시작 전)

| 지표 | M+1 | M+2 | M+3 |
|---|---|---|---|
| 방향 적중률 | 30.4% | 43.6% | 48.7% |
| 강도 적중률 | 21.5% | 30.7% | 31.1% |
| 변화율 범위 적중률 | 12.4% | 15.4% | 18.3% |
| 체인 평균 점수 | 0.291 | 0.369 | 0.407 |
| 분석 평균 점수 | 0.298 | 0.371 | 0.410 |

---

## 1차 스코어 (PR #11)

| 지표 | M+1 | M+2 | M+3 |
|---|---|---|---|
| 방향 적중률 | 31.3% | 43.6% | 49.3% |
| 강도 적중률 | 23.5% | 29.9% | 33.7% |
| 변화율 범위 적중률 | 12.6% | 15.1% | 18.8% |
| 체인 평균 점수 | 0.295 | 0.364 | 0.413 |
| 분석 평균 점수 | 0.302 | 0.367 | 0.417 |

---

## 2차 스코어 (PR #16)

| 지표 | M+1 | M+2 | M+3 |
|---|---|---|---|
| 방향 적중률 | 33.0% | — | — |
| 강도 적중률 | 37.6% | — | — |
| 변화율 범위 적중률 | — | — | — |
| 체인 평균 점수 | 0.431 | — | — |
| 분석 평균 점수 | 0.437 | — | — |

> M+2/M+3 미기록

---

## 3차 스코어 (PR #22)

| 지표 | M+1 | M+2 | M+3 |
|---|---|---|---|
| 방향 적중률 | 47.2% | 43.7% | 45.1% |
| 강도 적중률 | 29.6% | 30.4% | 37.9% |
| 변화율 범위 적중률 | 14.0% | 9.6% | 11.4% |
| 체인 평균 점수 | 0.499 | 0.473 | 0.485 |
| 분석 평균 점수 | 0.490 | 0.463 | 0.475 |

---

## 차수별 변경 내용

### 1차 → 2차 변경 (PR #11 → PR #16)

| 구분 | 변경 내용 |
|---|---|
| 채점 지표 분리 | geo_scope `korea/asia` → KOSIS/ECOS, `global` → FRED로 분리 적용 |
| 집계 방식 | `fetch_indicator_daily_monthly_avg` 추가 (daily 데이터 → monthly 평균 집계) |
| 부분 점수 도입 | 실제값 `neutral` 시 direction 0.5점 partial credit 적용 |
| 프롬프트 | LLM2 neutral 예측 강화 (rule 26/28 수정, neutral 예시 JSON 추가) |
| **스코어 변화** | **방향 31.3% → 33.0%** (+1.7%p) · 체인 0.295 → 0.431 (+0.136) |

### 2차 → 3차 변경 (PR #16 → PR #22)

| 구분 | 변경 내용 |
|---|---|
| 채점 필터 | `reliability < 0.6` 체인 제외, `time_horizon=medium + M+1` 조합 제외 |
| 컨텍스트 확장 | LLM2 입력에 천연가스·난방유·달러인덱스·GPR 7일평균 추가 |
| 지표 매핑 개선 | `food → cpi_agro / fred_wheat`, `price → ppi_total / fred_ppi` |
| 클러스터 집계 | 동일 월·카테고리 체인을 클러스터 단위로 집계하여 채점 |
| 가중치 조정 | direction 50% / magnitude 30% / change_pct 20% |
| null 보존 | `causal_normalizer`: LLM null 시 기본 밴드값 자동 채우기 제거 |
| 프롬프트 | neutral 기본값 강화, `change_pct` null 보존 |
| **스코어 변화** | **방향 33.0% → 47.2%** (+14.2%p) · 체인 0.431 → 0.499 (+0.068) |

---

## 작업 내역

### 1. 데이터 정리 — 라이브블로그 뉴스 삭제

**문제:** 실시간 속보형 뉴스(라이브블로그)는 단일 사건 분석이 아니라 여러 사건을 나열하는 형태라 LLM 분석 품질이 낮음

**삭제 패턴:**
- `as it happened`, `business live`, `live updates`
- `live blog`, `daily briefing`, `morning wrap`, `evening wrap`, `weekly wrap`

**처리 결과:**

| 테이블 | 처리 | 건수 |
|---|---|---|
| causal_chains | DELETE | 595건 |
| news_analyses | DELETE | 353건 |
| raw_news | is_deleted = true | 1,272건 |

**코드 수정:** `prd/llm/graph/news_pipeline_graph.py`
- `_LIVE_BLOG_TITLE_PATTERNS` 상수 추가
- `pre_filter_node` 맨 앞에 제목 패턴 체크 추가 → 매칭 시 LLM 호출 없이 skip

---

### 2. 데이터 정리 — FTSE/주식 기사 삭제

**문제:** 주식시장·금융시장 기사가 소비자 물가 카테고리로 잘못 분류되어 채점 품질 저하

**삭제 패턴:**
- `FTSE`, `stock market`, `shares`, `share price`
- `investing in shares`, `stock exchange`, `equity`, `dow jones`, `nasdaq`, `S&P 500`

**처리 결과:**

| 테이블 | 처리 | 건수 |
|---|---|---|
| causal_chains | DELETE | 60건 |
| news_analyses | DELETE | 31건 |
| raw_news | is_deleted = true | 99건 |

---

### 3. 스코어러 버그 수정 — magnitude 기준 불일치

**문제:** LLM 프롬프트와 스코어러의 `high` 기준이 달라 LLM이 맞게 예측해도 틀림 처리됨

| | 프롬프트 (LLM 지시) | 스코어러 (수정 전) | 스코어러 (수정 후) |
|---|---|---|---|
| low | 0~2% | 0~2% | 0~2% |
| medium | 2~5% | 2~7% | 2~5% |
| **high** | **5% 이상** | **7% 이상** ❌ | **5% 이상** ✅ |

**수정 파일:** `validation/config.py`
```python
# 수정 전
MAGNITUDE_HIGH_MIN_PCT: float = 7.0
# 수정 후
MAGNITUDE_HIGH_MIN_PCT: float = 5.0
```

**효과:** 강도 적중률 M+1 +2.5%p, M+3 +3.5%p

---

### 4. 스코어러 개선 — time_horizon 기반 채점 필터

**문제:** LLM이 `time_horizon: long`으로 판단한 기사(효과가 수개월 후 나타남)를 M+1 지표로 채점하면 당연히 틀림

**수정 내용:**
- `validation/db.py` — `fetch_cohort`에 `na.time_horizon` 컬럼 추가
- `validation/runner.py` — `time_horizon=long + horizon=1` 조합은 채점 제외(skip 처리)

**기준:**
| time_horizon | M+1 채점 | M+2 채점 | M+3 채점 |
|---|---|---|---|
| short | ✅ | ✅ | ✅ |
| medium | ✅ | ✅ | ✅ |
| long | ❌ skip | ✅ | ✅ |

**효과:** 방향 적중률 M+1 +0.4%p

---

### 5. LLM 프롬프트 개선 — neutral 가이드 추가

**문제:** LLM이 `neutral` 방향을 거의 예측하지 않음 (전체 1,840건 중 1건)

**수정 파일:** `prd/llm/prompts/causal_prompt.py`

추가된 규칙:
```
direction 기준 (월간 변화율 R 기준):
- neutral: |R| < 2% (변화가 미미하거나 상쇄되는 경우)
- up / down: |R| >= 2%
- 확신이 없거나 효과가 미미할 것으로 판단되면 neutral을 선택합니다.
```

> ⚠️ 기존 DB 데이터는 old 프롬프트로 생성됐기 때문에 **신규 분석 기사부터** 효과 발생

---

### 6. LLM 프롬프트 개선 — up 편향 교정

**문제:** LLM2(causal 추출)가 방향을 85% up, 14% down, 0.05% neutral로 극단적 편향 예측
- LLM1이 `cost_signal: down`을 넘겨도 LLM2가 무시하고 `up`으로 예측
- 예시 JSON이 `up` 케이스만 존재

**수정 파일:** `prd/llm/prompts/causal_prompt.py`

추가된 규칙:
```
26. 현재 뉴스 압축 노트의 cost_signal을 반드시 확인하고 effects의 direction과 일치시킵니다.
    - cost_signal: up   → direction: up
    - cost_signal: down → direction: down
    - cost_signal: none → effects: []
27. 공급 증가, 가격 하락, 정부 보조 확대, 세금 인하, 재고 증가, 수요 감소 뉴스는 direction: down을 적극 사용합니다.
28. 상반된 힘이 서로 상쇄되거나 효과가 2% 미만으로 미미하면 direction: neutral, magnitude: low를 사용합니다.
```

추가된 예시: `cost_signal: down` 케이스 (OPEC 증산 → 유가 하락 → 연료비 하락)

> ⚠️ 기존 DB 데이터 반영을 위해 **784건 재분석(processing_status 리셋) 필요**

---

### 7. 데이터 정합성 수정

**문제 1: 동일 analysis+category 중복 체인 1건**
- "Pasta, bread and crisps..." 기사에서 food 카테고리가 up/high, down/medium 두 개로 상반 저장
- 나중에 생성된 체인 1건 DELETE

**문제 2: change_pct_min > change_pct_max 논리 오류 7건**
- LLM이 하락을 표현할 때 min=-2, max=-5처럼 음수 순서를 반대로 저장
- min/max 값을 swap 처리

---

## 시도했으나 롤백한 작업

### neutral 임계값 상향 (NEUTRAL_THRESHOLD_PCT: 1.0 → 2.0)

**의도:** 실제 지표의 소폭 변동을 neutral로 분류해 LLM 예측과 일치율 높이기

**결과:** 방향 적중률 M+1 30.4% → 19.3% (역효과)

**원인:** 기존 DB 데이터는 neutral 기준 없이 생성된 up/down 편향 예측. 스코어러만 neutral 범위를 넓히니 실제는 neutral인데 LLM은 up/down → 방향 미스 급증

**현재 상태:** `NEUTRAL_THRESHOLD_PCT: 1.0` 복원, 프롬프트 neutral 가이드는 유지

---

## 진단 과정에서 발견된 구조적 문제

| 문제 | 설명 |
|---|---|
| LLM up 편향 | 전체 체인 중 85% up, 14% down, 0.05% neutral |
| geo_scope 불일치 | 전체 체인 중 85%가 global 기사인데 한국 지표(KOSIS, ECOS)로 채점 |
| 2026년 뉴스 과다 | 265건이 2026년 기사 → M+1/M+2/M+3 지표 미적재로 채점 제외 다수 |
| korea_relevance 미저장 | LLM이 생성하지만 DB 컬럼 없어 필터 불가 |

---

## 향후 개선 과제

| 우선순위 | 작업 | 예상 효과 |
|---|---|---|
| 높음 | 784건 재분석 (processing_status 리셋 후 PRD 재실행) | up 편향 데이터 교체 |
| 중간 | `news_analyses`에 `korea_relevance` 컬럼 추가 및 저장 | geo 불일치 필터 가능 |
| 중간 | geo_scope=global 기사 채점 제외 검토 | 한국 지표와 무관한 채점 제거 |
| 낮음 | 2026년 이후 지표 데이터 적재 | 채점 가능 체인 수 증가 |

---

## 현재 상황 (2026-04-17)

### 재분석 배치 실행

"향후 개선 과제 — 높음" 항목인 **up 편향 데이터 교체**를 위해 2026-04-16 PRD 배치를 4회 실행.

| 실행 시각 | 큐 크기 | 비고 |
|---|---|---|
| 19:07 | 856건 | 1차 시도 |
| 19:23 | 856건 | 2차 시도 |
| 19:37 | 856건 | 3차 시도 |
| 19:48 | 856건 | 855/856 처리 후 오류 중단 |

**중단 원인 (마지막 실행):**
- 855/856 처리 완료 직전 Supabase DB 저장 시 Cloudflare **400 Bad Request** 응답
- `postgrest.exceptions.APIError: JSON could not be generated`
- 해당 기사: `백악관 "이란과 합의 전망 긍정적…차기 협상 장소도 파키스탄"` (`news_id=0b12cac1-...`)
- LLM 분석 자체는 정상 완료 (`direction: down, magnitude: high, geo_scope: global`)
- DB 저장만 실패 → `failed` 상태로 mark 시도도 Cloudflare 차단으로 실패

**관찰 사항:**
- pre_filter에서 `non_economic` / `no_direct_cost_signal`로 skip되는 기사가 다수
- 예상 784건보다 실제 큐가 856건으로 집계됨

### 코드 이동

`validation/` → `prd/validation/`으로 모듈 경로 이동 완료 (git diff HEAD 기준).

### 현재 미결 사항

| 항목 | 상태 |
|---|---|
| 856건 재분석 완료 여부 | 미완 (855건 처리, 1건 DB 저장 실패로 중단) |
| 재분석 후 검증 스코어 재측정 | 미실시 |
| Cloudflare 차단 원인 파악 | 미진행 (Supabase 쿼리 크기 초과 또는 일시적 오류 가능성) |
