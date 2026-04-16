# Category → indicator mapping

Map each `cost_categories.code` / `causal_chains.category` value to **one** canonical indicator for scoring. **Prefer monthly tables** (see VALIDATION_PLAN §4.4).

**Status:** Rows below are **DRAFT v1** — confirm with domain owner before locking. Replace table/column names if your DB differs.

| category_code | indicator_table | time_key_column | value_column | R (v1) | Daily fallback |
|---------------|-----------------|-----------------|--------------|--------|----------------|
| oil | indicator_fred_monthly | reference_month | fred_wti | MoM %: `(v_{M+1}-v_M)/nullif(v_M,0)*100` | last obs / month |
| fuel | indicator_fred_monthly | reference_month | fred_ppi | same | last obs / month |
| energy | indicator_ecos_monthly | reference_date | ppi_energy | same (levels → %) | last obs / month |
| food | indicator_ecos_monthly | reference_date | import_price_food | same | last obs / month |
| wheat | indicator_fred_monthly | reference_month | fred_wheat | same | last obs / month |
| commodity | indicator_ecos_monthly | reference_date | ppi_total | same | last obs / month |
| shipping | indicator_fred_monthly | reference_month | fred_bdi | same | last obs / month |
| cost | indicator_kosis_monthly | reference_date | cpi_total | same | last obs / month |
| price | indicator_fred_monthly | reference_month | fred_cpi | same | last obs / month |
| inflation | indicator_fred_monthly | reference_month | fred_cpi | same | last obs / month |
| gas | indicator_ecos_monthly | reference_date | import_price_natural_gas | same | last obs / month |

If a `value_column` is often null for your window, pick an alternate from the same economic family and update this table.

## `related_indicators` policy (v1)

**Selected: Policy B** — If `news_analyses.related_indicators` contains a token that maps to a concrete series, **use that series for all chains under that analysis** (or only for chains whose category is compatible — choose one in code and document). Otherwise use the **category_code** row above.

**Token hints (extend in code):**

| Token | Suggested series |
|-------|------------------|
| wti | `indicator_fred_monthly.fred_wti` |
| usd_krw | `indicator_ecos_daily.krw_usd_rate` aggregated to monthly (last obs) — **note:** daily table; use monthly rule in §4.4 |
| gold | define when a gold column exists in your DB |

## Per-row notes (optional)

Add ε, magnitude overrides, or non–MoM R definitions here when a series is not in percentage points.

| category_code | Notes |
|---------------|-------|
| | |

## Date key normalization

- `reference_month` `YYYY-MM` → `(year, month)`.
- `reference_date` e.g. `YYYY-MM-01` → `date_trunc('month', date)`.
- Join news month **M** to indicator rows for the **same calendar month** consistently across tables.
