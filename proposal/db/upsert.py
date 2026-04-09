"""Postgres write helpers for proposal ingestion."""

from __future__ import annotations

def upsert_news(connection, news_list: list[dict[str, object]]) -> int:
    """Insert or update raw news rows keyed by `news_url`."""
    if not news_list:
        return 0

    by_url = {str(news["url"]): news for news in news_list}
    rows = [
        {
            "news_url": url,
            "title": news["title"],
            "content": news.get("content") or "",
            "origin_published_at": news.get("published_at"),
            "keyword": [],
        }
        for url, news in by_url.items()
    ]

    sql = """
        INSERT INTO raw_news (news_url, title, content, origin_published_at, keyword)
        VALUES (%(news_url)s, %(title)s, %(content)s, %(origin_published_at)s, %(keyword)s)
        ON CONFLICT (news_url) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            origin_published_at = COALESCE(EXCLUDED.origin_published_at, raw_news.origin_published_at),
            updated_at = NOW();
    """

    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)
    connection.commit()
    return len(rows)


def upsert_indicators(connection, indicators: list[dict[str, object]]) -> None:
    """Upsert hourly indicator rows by `(type, current UTC hour)` semantics."""
    if not indicators:
        return

    update_sql = """
        UPDATE economic_indicators AS ei
        SET value = %(value)s,
            unit = %(unit)s,
            source = %(source)s,
            updated_at = NOW()
        FROM (
            SELECT id
            FROM economic_indicators
            WHERE type = %(type)s
              AND date_trunc('hour', recorded_at AT TIME ZONE 'UTC')
                  = date_trunc('hour', NOW() AT TIME ZONE 'UTC')
            ORDER BY recorded_at DESC
            LIMIT 1
        ) AS sub
        WHERE ei.id = sub.id;
    """
    insert_sql = """
        INSERT INTO economic_indicators (type, value, unit, source)
        VALUES (%(type)s, %(value)s, %(unit)s, %(source)s);
    """

    with connection.cursor() as cursor:
        for row in indicators:
            cursor.execute(update_sql, row)
            if cursor.rowcount == 0:
                cursor.execute(insert_sql, row)
    connection.commit()
