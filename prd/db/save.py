"""Postgres write helpers for PRD analysis."""

from __future__ import annotations


def save_analysis_result(connection, raw_news_id: str, result: dict) -> None:
    """Insert one analysis row and its causal effect rows in a single transaction."""
    sql_analysis = """
        INSERT INTO news_analyses (raw_news_id, summary, reliability, related_indicators)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """
    sql_causal = """
        INSERT INTO causal_chains
            (news_analysis_id, event, mechanism,
             category, direction, magnitude,
             change_pct_min, change_pct_max, monthly_impact)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql_analysis,
                (
                    raw_news_id,
                    result.get("summary", ""),
                    float(result.get("reliability", 0.85)),
                    result.get("related_indicators", []),
                ),
            )
            analysis_id = cursor.fetchone()[0]

        with connection.cursor() as cursor:
            for effect in result.get("effects", []):
                cursor.execute(
                    sql_causal,
                    (
                        analysis_id,
                        result.get("event", ""),
                        result.get("mechanism", ""),
                        effect.get("category", ""),
                        effect.get("direction", "neutral"),
                        effect.get("magnitude", "low"),
                        effect.get("change_pct_min"),
                        effect.get("change_pct_max"),
                        effect.get("monthly_impact"),
                    ),
                )

        connection.commit()
    except Exception:
        connection.rollback()
        raise


def mark_as_processing(connection, raw_news_id: str) -> None:
    """Mark a raw news row as in-progress before LLM analysis."""
    sql = """
        UPDATE raw_news
        SET processing_status = 'processing',
            updated_at = NOW()
        WHERE id = %s;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, (raw_news_id,))
    connection.commit()


def mark_as_processed(connection, raw_news_id: str) -> None:
    """Mark a raw news row as successfully processed."""
    sql = """
        UPDATE raw_news
        SET processing_status = 'processed',
            processing_error  = NULL,
            processed_at      = NOW(),
            updated_at        = NOW()
        WHERE id = %s;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, (raw_news_id,))
    connection.commit()


def mark_as_failed(connection, raw_news_id: str, error_msg: str) -> None:
    """Mark a raw news row as failed and increment retry_count."""
    sql = """
        UPDATE raw_news
        SET processing_status = 'failed',
            processing_error  = %s,
            retry_count       = COALESCE(retry_count, 0) + 1,
            updated_at        = NOW()
        WHERE id = %s;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, (error_msg[:1000], raw_news_id))
    connection.commit()

