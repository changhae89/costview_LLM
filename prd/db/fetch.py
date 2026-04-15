"""Read helper queries for PRD analysis."""

from __future__ import annotations

from psycopg.rows import dict_row


def fetch_pending_news(connection, limit: int = 20) -> list[dict]:
    """Fetch undeleted raw news rows that do not yet have an analysis record."""
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
        WHERE NOT EXISTS (SELECT 1 FROM news_analyses na WHERE na.raw_news_id = rn.id)
          AND COALESCE(rn.is_deleted, false) = false
        ORDER BY rn.created_at ASC
        LIMIT %s;
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def fetch_active_cost_categories(connection) -> list[str]:
    """Fetch active cost category codes ordered for prompt usage."""
    sql = """
        SELECT code
        FROM cost_categories
        WHERE is_active = true
        ORDER BY sort_order ASC, code ASC;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [str(row[0]).strip() for row in cursor.fetchall() if str(row[0]).strip()]


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
