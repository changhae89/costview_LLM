# 경제 지표 컨텍스트 주입 기획서

## 목적

LLM2(causal chain)가 뉴스 발행 당시의 실제 경제 지표를 참조하여
`change_pct_min`, `change_pct_max`, `monthly_impact`를 더 정확하게 추정하도록 한다.

---

## 현재 문제

- LLM2는 뉴스 텍스트와 과거 분석 컨텍스트만 참조
- 당시 유가, 환율, CPI 등 실제 수치 없이 추론 → 수치 정확도 낮음
- 1999년 코소보 전쟁 뉴스: 당시 WTI, KRW/USD를 모르므로 `monthly_impact` 추정 불가

---

## 사용할 지표 테이블

| 테이블 | 주요 컬럼 | 주기 | 시작 연도 |
|--------|-----------|------|-----------|
| `indicator_ecos_daily_logs` | `krw_usd_rate` | 일별 | 1964 |
| `indicator_ecos_monthly_logs` | `import_price_crude_oil`, `import_price_natural_gas` | 월별 | 1971 |
| `indicator_kosis_monthly_logs` | `cpi_total`, `core_cpi`, `cpi_petroleum`, `cpi_agro` | 월별 | 1985 |
| `indicator_fred_daily_logs` | `fred_wti`, `fred_usd_index` | 일별 | 2014 |
| `indicator_fred_monthly_logs` | `fred_cpi`, `fred_fedfunds`, `fred_gepu` | 월별 | 2014 |
| `indicator_gpr_monthly_logs` | `gpr_original`, `oil_disruptions` | 월별 | 1960 |

---

## 조회 전략

뉴스 `published_at` 기준으로 가장 가까운 데이터를 조회한다.

| 지표 | 조회 방식 | 우선순위 |
|------|-----------|----------|
| 유가(WTI) | `indicator_fred_daily_logs.fred_wti` (없으면 `indicator_ecos_monthly_logs.import_price_crude_oil`) | 1순위 |
| 환율(KRW/USD) | `indicator_ecos_daily_logs.krw_usd_rate` | 필수 |
| 한국 CPI | `indicator_kosis_monthly_logs.cpi_total` | 필수 |
| 지정학적 리스크(GPR) | `indicator_gpr_monthly_logs.gpr_original` | 있으면 포함 |
| 원유 수입가 | `indicator_ecos_monthly_logs.import_price_crude_oil` | 있으면 포함 |

---

## 반환 형식 (fetch_indicators_by_date 결과)

```python
{
    "reference_date": "1999-01-15",
    "krw_usd_rate": 1200.5,          # 환율 (원/달러)
    "wti": 14.2,                      # WTI 유가 (달러/배럴), None이면 생략
    "crude_import_price": 13.8,       # 원유 수입가, None이면 생략
    "cpi_total": 65.3,                # 한국 CPI, None이면 생략
    "gpr": 145.2,                     # 지정학적 리스크 지수, None이면 생략
}
```

---

## 그래프 변경

```
START
  │
  ▼
summarize
  │
  ▼
build_history_context        (기존)
  │
  ▼
build_indicator_context      ← 신규 노드 (DB READ)
  │
  ▼
extract_causal               (LLM2, indicator_context 추가)
  │
  ▼
validate_causal
  ...
```

---

## 프롬프트 변경 (LLM2 추가 섹션)

```
[경제 지표 — 뉴스 발행 당시]
- 날짜: 1999-01-15
- KRW/USD 환율: 1,200.5원
- WTI 유가: $14.2/배럴
- 한국 CPI: 65.3
- 지정학적 리스크(GPR): 145.2
```

추가 규칙:
- 지표가 있으면 `monthly_impact` 계산 시 실제 수치를 근거로 사용하세요.
- 지표가 없는 시기(None)는 뉴스 맥락만으로 추정하세요.

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `db/fetch.py` | `fetch_indicators_by_date()` 추가 |
| `db/supabase_store.py` | `fetch_indicators_by_date_sb()` 추가 |
| `db/repository.py` | Protocol에 `fetch_indicators_by_date()` 추가 |
| `db/postgres_repository.py` | 구현체 추가 |
| `db/supabase_repository.py` | 구현체 추가 |
| `llm/graph/news_pipeline_graph.py` | `build_indicator_context_node` 신규, `NewsState` 필드 추가 |
| `llm/prompts/causal_prompt.py` | `{indicator_context}` 섹션 추가 |
| `llm/chains/llm_runner.py` | `run_causal_chain(indicator_context=)` 파라미터 추가 |

---

## 예상 효과

| 항목 | 개선 전 | 개선 후 |
|------|---------|---------|
| `monthly_impact` 정확도 | LLM 추측 | 실제 환율·유가 기반 계산 |
| 1999년 이전 뉴스 | 지표 없어 추정 | 가능한 지표 최대 활용 |
| `reliability` 신뢰도 | 텍스트 기반 | 수치 근거 보정 가능 |
| skip 비율 | 높음 | 실제 수치로 영향 추정 가능 → 감소 |

---

## 데이터 공백 처리 원칙

- 지표가 NULL이면 해당 항목 프롬프트에서 생략
- 모든 지표가 NULL이면 `[경제 지표]` 섹션 자체를 "데이터 없음"으로 표시
- `fetch_indicators_by_date`는 항상 dict를 반환 (빈 dict 아님, None 값 포함)
