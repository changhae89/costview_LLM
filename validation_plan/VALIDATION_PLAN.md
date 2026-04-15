[//]: # (File encoding: UTF-8, no BOM. Root .editorconfig applies.)

# News analysis backtest — validation plan

*(Validation / backtest specification.)*

## 1. Purpose

Quantify how well stored LLM outputs (`news_analyses`, `causal_chains`) align with **realized macro and price indicators** over a **calendar month horizon (M → M+1)**. Provide a **reproducible baseline** when changing models, prompts, or category logic.

## 2. Scope

**In scope**

- Rows in `raw_news` → `news_analyses` → `causal_chains`.
- Monthly (primary) and daily (fallback) indicator tables already in the database.

**Out of scope (initially)**

- Claims with **no mapped indicator** (manual labels or secondary LLM review — future work).
- Causal interpretation beyond **statistical alignment** (correlation / hit rate, not proof of causation).

## 3. Definitions

| Term | Definition |
|------|------------|
| **as-of** | `raw_news.origin_published_at` (timezone must be fixed; default **UTC** unless product says otherwise). |
| **Calendar month M** | The calendar month containing **as-of** (e.g. 2025-01-15 → M = 2025-01). |
| **Horizon** | **M → M+1**: compare indicator values for month **M** and month **M+1**. |
| **Validation unit** | One aggregate score per **`news_analysis_id`** (see §4.2). |
| **Realized value R** | A scalar change derived from the chosen indicator between M and M+1 (e.g. level diff, log diff, MoM %). **Same formula in code and this doc.** |

**Timezone (verify in DB):** Confirm whether `origin_published_at` is stored as `timestamptz` and which zone writers use. All month buckets **M** must use one convention (recommended: **UTC** for `date_trunc`, documented in code).

## 4. Agreed rules

### 4.1 Horizon

- **Calendar M → M+1** only (not 30 calendar days, not N business days).

### 4.2 Aggregation — method **B**

- A single analysis can have **multiple** `causal_chains` rows (different `category`, etc.).
- For **each chain row** that can be scored (category has a mapped indicator and M/M+1 data exist), compute a **partial score** (§4.3).
- **`news_analysis_id` final score** = aggregate of partial scores over **eligible** chains only (e.g. **unweighted mean** of partial scores; weighting table can be added later).
- Chains with **no indicator** or **missing M/M+1** are **excluded from the denominator** (average over chains that could be scored).

### 4.3 Score components (use all three where applicable)

For each scorable chain:

1. **Direction** — model `direction` (up / down / neutral) vs sign of **R** (or band for “neutral”; define thresholds once).
2. **Magnitude** — map |R| to low / medium / high buckets; compare to chain `magnitude` (bucket boundaries: fixed rules or data-driven; document choice).
3. **`change_pct_min` / `change_pct_max`**
   - If **both are NULL** → **do not score this component** (skip; do not treat as pass).
   - If at least one is set → **pass** if R lies in the interval between min and max using the **v1 boundary rule** below.

**Chain-level combination (v1 default — revise after first calibration run):**

- Each active component yields **0 or 1** (direction, magnitude, change_pct when not skipped).
- **Partial chain score** = arithmetic mean of active components only (e.g. if change_pct skipped: `(dir + mag) / 2`).
- **Alternative (stricter, optional flag):** geometric mean or product `dir * mag * pct` so one miss fails all; document if enabled.
- **`news_analysis_id` score** remains the mean of eligible chains’ partial scores (§4.2).

**Direction and “neutral” (v1 default):**

- Compute R in a **documented unit** (prefer **MoM %** for level series: `(v_{M+1} - v_M) / nullif(v_M, 0)`).
- **Realized neutral band:** treat R as **neutral** if `abs(R) < 0.5` when R is expressed in **percentage points** (i.e. |R| < 0.5%). If R is not in %, convert or define an equivalent ε for that series once in the mapping table.
- Match model `neutral` to realized neutral; **up** if `R ≥ +0.5%`, **down** if `R ≤ -0.5%` (adjust if ε changes).

**Magnitude buckets for absolute move (v1 default, when R is MoM % in percentage points):**

| Bucket | abs(R) range (pp) |
|--------|-------------------|
| low | `< 1` |
| medium | `≥ 1` and `< 5` |
| high | `≥ 5` |

If a series uses levels or YoY % instead, define parallel thresholds in [category_indicator_mapping.md](./category_indicator_mapping.md) per row.

**`change_pct` interval (v1 default):**

- **Closed interval:** pass iff `min ≤ R ≤ max` when both min and max are present; if only one bound is set, treat missing bound as unbounded on that side but still document in code (e.g. only `min` → `R ≥ min`).

### 4.4 Indicator source priority

1. **Prefer monthly** tables (`indicator_*_monthly*`, `reference_month` as `YYYY-MM`, or `reference_date` like `YYYY-MM-01`). Aligns with M → M+1.
2. **Use daily** only if the concept is **missing** on monthly or M/M+1 is **null** on monthly. Aggregate daily to **one number per month** with a **fixed rule** (e.g. **last observation in month** for prices; document if month-average is used instead).
3. **One canonical source per economic concept** — do not double-count monthly and daily for the same concept.

### 4.5 Date normalization

Indicator tables use mixed string formats (`YYYY-MM`, `YYYY-MM-DD`, etc.). Implement a **single normalization layer** (parse → `year-month` key) before joining to news month M and M+1.

## 5. Process

1. **Extract** `raw_news` → `news_analyses` → `causal_chains` with filters (`is_deleted = false` or `COALESCE(rn.is_deleted, false) = false` if the column is nullable — confirm actual `raw_news` DDL), optional `origin_published_at >= :start`.
2. **Derive** `M = date_trunc('month', origin_published_at)` (consistent timezone).
3. **Map** each chain `category` to indicator via [category_indicator_mapping.md](./category_indicator_mapping.md), including **`related_indicators` policy** (v1 draft: **Policy B** — override when tokens match; confirm with product).
4. **Fetch** indicator rows for **M** and **M+1** for each mapped series.
5. **Compute R** and partial scores; then **aggregate per `news_analysis_id`** (method B).
6. **Report** hit rates, coverage (how many chains skipped), and optional per-analysis CSV for debugging.

## 6. Deliverables

- Configurable **batch report** for a date range: summary stats + component-level hit rates + missing-data rates.
- Optional **per-`news_analysis_id` detail** export.

## 7. Risks and constraints

- **Stale / missing M+1** — skip or defer scoring until data exists.
- **Look-ahead bias** — offline reruns must use only data available at as-of (pipeline discipline).
- **Multiple chains** — method B can dilute or amplify single strong effects; interpret aggregates accordingly.
- **Indicator nulls** — recent daily rows may have null oil fields, etc.; handle with skip or forward-fill **only if explicitly allowed**.

## 8. Follow-ups

- Variable horizons; auto-sync mapping with `related_indicators`.
- Qualitative check using follow-up news in the window.
- Link to `prd/evals` if product wants a single eval entry point.

## 9. Open decisions / calibration (post–v1 run)

The following are **defaults to unblock implementation**; revisit after enough scored rows exist.

| Topic | v1 default in this doc | Review trigger |
|--------|------------------------|----------------|
| Component combination | Mean of active 0/1 parts; optional strict product mode | Distribution of partial scores |
| ε for direction neutral | 0.5% in MoM % units | Residual false “neutral” rate |
| Magnitude cutoffs | 1% / 5% on \|R\| | Per-category calibration |
| Mapping rows | DRAFT in mapping file | Domain expert sign-off |
| Policy A vs B | **Policy B** | Conflicts between `related_indicators` and category |

## 10. Change log

| Date | Change |
|------|--------|
| 2026-04-15 | Initial plan: M→M+1, method B, skip pct when both NULL, monthly-first indicators. |
| 2026-04-16 | v1 scoring defaults (mean, neutral ε, magnitude bands, inclusive bounds); mapping DRAFT + Policy B; DB/timezone/is_deleted notes. |
