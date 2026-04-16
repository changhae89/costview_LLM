"""Postgres write helpers for PRD analysis."""

from __future__ import annotations


def save_analysis_result(connection, raw_news_id: str, result: dict) -> None:
    """Upsert one analysis row and its causal effect rows in a single transaction.

    If news_analyses already exists for raw_news_id, updates it and replaces
    causal_chains. Otherwise inserts fresh rows.
    """
    sql_get = "SELECT id FROM news_analyses WHERE raw_news_id = %s LIMIT 1;"
    sql_insert = """
        INSERT INTO news_analyses (
            raw_news_id, summary, reliability, related_indicators,
            reliability_reason, time_horizon, effect_chain,
            buffer, leading_indicator, geo_scope
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
    sql_update = """
        UPDATE news_analyses
        SET summary            = %s,
            reliability        = %s,
            related_indicators = %s,
            reliability_reason = %s,
            time_horizon       = %s,
            effect_chain       = %s,
            buffer             = %s,
            leading_indicator  = %s,
            geo_scope          = %s,
            updated_at         = NOW()
        WHERE id = %s
        RETURNING id;
    """
    sql_delete_chains = "DELETE FROM causal_chains WHERE news_analysis_id = %s;"
    sql_causal = """
        INSERT INTO causal_chains
            (news_analysis_id, event, mechanism,
             category, direction, magnitude,
             change_pct_min, change_pct_max, monthly_impact)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    try:
        import json as _json
        effect_chain = result.get("effect_chain") or []
        effect_chain_json = _json.dumps(effect_chain, ensure_ascii=False)
        common_fields = (
            result.get("summary", ""),
            float(result.get("reliability", 0.85)),
            result.get("related_indicators") or [],
            result.get("reliability_reason") or "",
            result.get("time_horizon"),
            effect_chain_json,
            result.get("buffer") or "",
            result.get("leading_indicator"),
            result.get("geo_scope"),
        )

        with connection.cursor() as cursor:
            cursor.execute(sql_get, (raw_news_id,))
            row = cursor.fetchone()

        with connection.cursor() as cursor:
            if row:
                analysis_id = row[0]
                cursor.execute(sql_update, (*common_fields, analysis_id))
                cursor.execute(sql_delete_chains, (analysis_id,))
            else:
                cursor.execute(sql_insert, (raw_news_id, *common_fields))
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


def mark_as_skipped(connection, raw_news_id: str) -> None:
    """Mark a raw news row as skipped (LLM returned empty effects)."""
    sql = """
        UPDATE raw_news
        SET processing_status = 'skipped',
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

