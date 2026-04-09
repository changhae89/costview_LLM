"""Read helper queries for proposal ingestion."""

from __future__ import annotations

from psycopg.rows import dict_row


def fetch_consumer_keywords(
    connection,
    category: str = "소비재",
    limit: int = 30,
) -> list[str]:
    """Fetch active consumer-item keywords for the requested category."""
    sql = """
        SELECT keyword
        FROM consumer_items
        WHERE category = %s
          AND COALESCE(is_deleted, false) = false
          AND NULLIF(BTRIM(keyword), '') IS NOT NULL
        ORDER BY keyword ASC
        LIMIT %s;
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, (category, limit))
        rows = cursor.fetchall()

    return [str(row["keyword"]).strip() for row in rows if row.get("keyword")]
