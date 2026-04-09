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
               rn.created_at
        FROM raw_news rn
        WHERE NOT EXISTS (SELECT 1 FROM news_analyses na WHERE na.raw_news_id = rn.id)
          AND COALESCE(rn.is_deleted, false) = false
        ORDER BY rn.created_at ASC
        LIMIT %s;
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]

