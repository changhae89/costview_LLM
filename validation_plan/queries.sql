-- validation_plan: reference SQL for backtest / validation (PostgreSQL)
-- Encoding: UTF-8. Adjust schema, timezone, and names to match your database.
-- If raw_news.is_deleted is NOT NULL with default false, you can use `rn.is_deleted = false` instead of COALESCE.

-- ---------------------------------------------------------------------------
-- 1) Backtest cohort: news + analysis + chains from a start timestamp (runnable example)
-- ---------------------------------------------------------------------------
-- Example start: TIMESTAMPTZ '2025-01-01 00:00:00+00'

SELECT
  rn.id              AS raw_news_id,
  rn.origin_published_at,
  date_trunc('month', rn.origin_published_at)::date AS news_month_m,
  na.id              AS news_analysis_id,
  na.summary,
  na.related_indicators,
  cc.id              AS causal_chain_id,
  cc.category,
  cc.direction,
  cc.magnitude,
  cc.change_pct_min,
  cc.change_pct_max,
  cc.monthly_impact
FROM raw_news rn
JOIN news_analyses na ON na.raw_news_id = rn.id
JOIN causal_chains cc ON cc.news_analysis_id = na.id
WHERE COALESCE(rn.is_deleted, false) = false
  AND rn.origin_published_at >= TIMESTAMPTZ '2025-01-01 00:00:00+00'
ORDER BY rn.origin_published_at, na.id, cc.id
LIMIT 500;

-- ---------------------------------------------------------------------------
-- 2) Example: two months for FRED monthly (reference_month = 'YYYY-MM')
-- ---------------------------------------------------------------------------

/*
SELECT *
FROM indicator_fred_monthly
WHERE reference_month IN ('2025-01', '2025-02');
*/

-- ---------------------------------------------------------------------------
-- 3) Dump column list (when schema changes)
-- ---------------------------------------------------------------------------

/*
SELECT
  table_name,
  ordinal_position,
  column_name,
  data_type,
  character_maximum_length,
  numeric_precision,
  numeric_scale,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
*/

-- ---------------------------------------------------------------------------
-- 4) Optional: UNION “sample all tables” query for one-shot QA
-- ---------------------------------------------------------------------------
-- Paste and maintain the project UNION query; fix aliases if it conflicts with DB.
