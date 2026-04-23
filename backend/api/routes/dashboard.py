from fastapi import APIRouter, Depends

from auth import require_auth
from db import get_conn

router = APIRouter(dependencies=[Depends(require_auth)])


def _rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _latest_metric(cur, table: str, value_col: str) -> list[dict]:
    cur.execute(
        f"""
        SELECT {value_col}, reference_date
        FROM {table}
        WHERE {value_col} IS NOT NULL
        ORDER BY reference_date::date DESC
        LIMIT 2
        """
    )
    return _rows(cur)


@router.get("/kpi")
def get_kpi_latest():
    with get_conn() as conn:
        with conn.cursor() as cur:
            return {
                "global_risk": _latest_metric(cur, "indicator_gpr_daily_logs", "ai_gpr_index"),
                "exchange_rate": _latest_metric(cur, "indicator_ecos_daily_logs", "krw_usd_rate"),
                "wti": _latest_metric(cur, "indicator_fred_daily_logs", "fred_wti"),
                "cpi": _latest_metric(cur, "indicator_kosis_monthly_logs", "cpi_total"),
                "treasury_10y": _latest_metric(cur, "indicator_fred_daily_logs", "fred_treasury_10y"),
            }


@router.get("/pipeline-stats")
def get_pipeline_stats():
    counts = {"processed": 0, "skipped": 0, "pending": 0, "failed": 0}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(processing_status, 'pending') AS status, COUNT(*)
                FROM raw_news
                GROUP BY COALESCE(processing_status, 'pending')
                """
            )
            for status, count in cur.fetchall():
                counts[status] = count
    return counts


@router.get("/gpr-trend")
def get_gpr_trend(days: int = 30):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ai_gpr_index, reference_date
                FROM indicator_gpr_daily_logs
                WHERE reference_date::date >= CURRENT_DATE - (%s::int * INTERVAL '1 day')
                ORDER BY reference_date ASC
                """,
                (days,),
            )
            return _rows(cur)


@router.get("/causal-summary")
def get_causal_summary():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT category, direction, magnitude, news_analysis_id FROM causal_chains")
            return _rows(cur)


@router.get("/recent-analyses")
def get_recent_analyses(limit: int = 5):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  na.id,
                  na.summary,
                  na.reliability,
                  na.created_at,
                  json_build_object(
                    'title', rn.title,
                    'origin_published_at', rn.origin_published_at
                  ) AS raw_news,
                  COALESCE(
                    json_agg(json_build_object('category', cc.category, 'direction', cc.direction))
                      FILTER (WHERE cc.id IS NOT NULL),
                    '[]'::json
                  ) AS causal_chains
                FROM news_analyses na
                LEFT JOIN raw_news rn ON rn.id = na.raw_news_id
                LEFT JOIN causal_chains cc ON cc.news_analysis_id = na.id
                GROUP BY na.id, rn.title, rn.origin_published_at
                ORDER BY na.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return _rows(cur)
