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


def mark_as_processed(connection, raw_news_id: str) -> None:
    """Mark a raw news row as successfully processed when status columns are available."""
    _update_raw_news_status(
        connection,
        raw_news_id=raw_news_id,
        status="processed",
        error_message=None,
    )


def mark_as_failed(connection, raw_news_id: str, error_msg: str) -> None:
    """Mark a raw news row as failed when status columns are available."""
    _update_raw_news_status(
        connection,
        raw_news_id=raw_news_id,
        status="failed",
        error_message=error_msg[:1000],
    )


def _update_raw_news_status(
    connection,
    *,
    raw_news_id: str,
    status: str,
    error_message: str | None,
) -> None:
    """Best-effort status update that becomes a no-op when the schema lacks status columns."""
    sql = """
        UPDATE raw_news
        SET processing_status = %s,
            processing_error = %s,
            processed_at = CASE WHEN %s = 'processed' THEN NOW() ELSE processed_at END,
            updated_at = NOW()
        WHERE id = %s;
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (status, error_message, status, raw_news_id))
        connection.commit()
    except Exception:
        connection.rollback()

