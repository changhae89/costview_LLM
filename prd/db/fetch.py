"""Read helper queries for PRD analysis."""

from __future__ import annotations

from datetime import date as DateType

from psycopg.rows import dict_row


def count_pending_news(connection) -> int:
    """Count rows that fetch_pending_news would return (same filters)."""
    sql = """
        SELECT COUNT(*)::bigint
        FROM raw_news rn
        WHERE COALESCE(rn.is_deleted, false) = false
          AND rn.processing_status IS NULL;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0


def fetch_pending_news(connection, *, limit: int = 10) -> list[dict]:
    """Fetch unprocessed raw news rows up to limit (excludes failed/skipped/processed/processing/deleted)."""
    sql = """
        SELECT rn.id,
               rn.news_url AS url,
               rn.title,
               CAST(NULL AS VARCHAR(200)) AS source,
               rn.content,
               rn.origin_published_at AS published_at,
               rn.created_at,
               rn.keyword
        FROM raw_news rn
        WHERE COALESCE(rn.is_deleted, false) = false
          AND rn.processing_status IS NULL
        ORDER BY rn.origin_published_at ASC
        LIMIT %s;
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def fetch_active_cost_categories(connection) -> list[dict]:
    """Fetch active cost categories with labels and keywords for prompt usage."""
    sql = """
        SELECT code, name_ko, keywords
        FROM cost_categories
        WHERE is_active = true
        ORDER BY sort_order ASC, code ASC;
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall() if str(row.get("code", "")).strip()]


def fetch_analysis_history(
    connection,
    *,
    current_news_id: str,
    keywords: list[str] | None,
    published_at,
    limit: int = 5,
) -> list[dict]:
    """
    Fetch previously analyzed related news using raw_news keyword overlap.
    Context uses news_analyses + causal_chains instead of raw content.
    """
    safe_keywords = [str(item).strip() for item in (keywords or []) if str(item).strip()]
    sql = """
        SELECT
            rn.id AS raw_news_id,
            rn.title,
            rn.origin_published_at AS published_at,
            na.id AS analysis_id,
            na.summary,
            na.reliability,
            na.related_indicators,
            cc.category,
            cc.direction,
            cc.magnitude,
            cc.change_pct_min,
            cc.change_pct_max,
            cc.monthly_impact
        FROM raw_news rn
        JOIN news_analyses na
          ON na.raw_news_id = rn.id
        LEFT JOIN causal_chains cc
          ON cc.news_analysis_id = na.id
        WHERE rn.id <> %s
          AND COALESCE(rn.is_deleted, false) = false
          AND (%s::timestamptz IS NULL OR rn.origin_published_at <= %s::timestamptz)
          AND (
                COALESCE(array_length(%s::text[], 1), 0) = 0
                OR rn.keyword && %s::text[]
              )
        ORDER BY rn.origin_published_at DESC NULLS LAST, na.created_at DESC
        LIMIT %s;
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            sql,
            (
                current_news_id,
                published_at,
                published_at,
                safe_keywords,
                safe_keywords,
                limit,
            ),
        )
        rows = [dict(row) for row in cursor.fetchall()]
    return _group_analysis_history(rows)


def fetch_indicators_by_date(connection, *, reference_date: str) -> dict:
    """Fetch 12-month monthly series of economic indicators up to reference_date."""

    def _series(cursor, sql: str, params: tuple) -> list[tuple[str, float]]:
        cursor.execute(sql, params)
        return [(row["month"], float(row["value"])) for row in cursor.fetchall()]

    with connection.cursor(row_factory=dict_row) as cursor:
        _series(cursor, """
            SELECT to_char(date_trunc('month', reference_date), 'YYYY-MM') AS month,
                   AVG(krw_usd_rate) AS value
            FROM indicator_ecos_daily_logs
            WHERE reference_date >= date_trunc('month', %s::date) - INTERVAL '11 months'
              AND reference_date <= %s::date
            GROUP BY date_trunc('month', reference_date)
            ORDER BY month;
        """, (reference_date, reference_date))
        krw_usd_rate = [(r["month"], float(r["value"])) for r in cursor.fetchall()]

        _series(cursor, """
            SELECT to_char(reference_date, 'YYYY-MM') AS month,
                   import_price_crude_oil AS value
            FROM indicator_ecos_monthly_logs
            WHERE reference_date >= date_trunc('month', %s::date) - INTERVAL '11 months'
              AND reference_date <= date_trunc('month', %s::date)
              AND import_price_crude_oil IS NOT NULL
            ORDER BY reference_date;
        """, (reference_date, reference_date))
        wti = [(r["month"], float(r["value"])) for r in cursor.fetchall()]

        _series(cursor, """
            SELECT to_char(reference_date, 'YYYY-MM') AS month,
                   cpi_total AS value
            FROM indicator_kosis_monthly_logs
            WHERE reference_date >= date_trunc('month', %s::date) - INTERVAL '11 months'
              AND reference_date <= date_trunc('month', %s::date)
              AND cpi_total IS NOT NULL
            ORDER BY reference_date;
        """, (reference_date, reference_date))
        cpi_total = [(r["month"], float(r["value"])) for r in cursor.fetchall()]

        _series(cursor, """
            SELECT to_char(reference_date, 'YYYY-MM') AS month,
                   gpr_original AS value
            FROM indicator_gpr_monthly_logs
            WHERE reference_date >= date_trunc('month', %s::date) - INTERVAL '11 months'
              AND reference_date <= date_trunc('month', %s::date)
              AND gpr_original IS NOT NULL
            ORDER BY reference_date;
        """, (reference_date, reference_date))
        gpr = [(r["month"], float(r["value"])) for r in cursor.fetchall()]

        _series(cursor, """
            SELECT to_char(date_trunc('month', reference_date), 'YYYY-MM') AS month,
                   AVG(fred_wti) AS value
            FROM indicator_fred_daily_logs
            WHERE reference_date >= date_trunc('month', %s::date) - INTERVAL '11 months'
              AND reference_date <= %s::date
              AND fred_wti IS NOT NULL
            GROUP BY date_trunc('month', reference_date)
            ORDER BY month;
        """, (reference_date, reference_date))
        fred_wti = [(r["month"], float(r["value"])) for r in cursor.fetchall()]

        _series(cursor, """
            SELECT reference_month AS month, fred_cpi AS value
            FROM indicator_fred_monthly_logs
            WHERE reference_month >= to_char(date_trunc('month', %s::date) - INTERVAL '11 months', 'YYYY-MM')
              AND reference_month <= to_char(date_trunc('month', %s::date), 'YYYY-MM')
              AND fred_cpi IS NOT NULL
            ORDER BY reference_month;
        """, (reference_date, reference_date))
        fred_cpi = [(r["month"], float(r["value"])) for r in cursor.fetchall()]

    return {
        "reference_date": reference_date,
        "krw_usd_rate": krw_usd_rate,
        "wti": wti,
        "cpi_total": cpi_total,
        "gpr": gpr,
        "fred_wti": fred_wti,
        "fred_cpi": fred_cpi,
    }


def _group_analysis_history(rows: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        analysis_id = str(row["analysis_id"])
        item = grouped.setdefault(
            analysis_id,
            {
                "raw_news_id": row["raw_news_id"],
                "title": row["title"],
                "published_at": row["published_at"],
                "analysis_id": row["analysis_id"],
                "summary": row["summary"],
                "reliability": float(row["reliability"] or 0),
                "related_indicators": row.get("related_indicators") or [],
                "effects": [],
            },
        )
        if row.get("category"):
            item["effects"].append(
                {
                    "category": row["category"],
                    "direction": row["direction"],
                    "magnitude": row["magnitude"],
                    "change_pct_min": row["change_pct_min"],
                    "change_pct_max": row["change_pct_max"],
                    "monthly_impact": row["monthly_impact"],
                }
            )
    return list(grouped.values())
