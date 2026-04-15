"""DB fetch helpers for validation backtest (read-only)."""
from __future__ import annotations

import psycopg2.extras

from .mapping import _ALLOWED_COLUMNS, _ALLOWED_TABLES


def fetch_cohort(connection, *, start: str, end: str | None = None) -> list[dict]:
    """Fetch news + analyses + chains for the backtest date range.

    Args:
        start: inclusive lower bound, e.g. '2025-01-01'
        end:   exclusive upper bound, e.g. '2026-01-01' (omit for open-ended)
    """
    sql = """
        SELECT
            rn.id                                                               AS raw_news_id,
            rn.origin_published_at,
            date_trunc('month', rn.origin_published_at AT TIME ZONE 'UTC')::date AS news_month_m,
            na.id                                                               AS news_analysis_id,
            cc.id                                                               AS causal_chain_id,
            cc.category,
            cc.direction,
            cc.magnitude,
            cc.change_pct_min,
            cc.change_pct_max
        FROM raw_news rn
        JOIN news_analyses na ON na.raw_news_id = rn.id
        JOIN causal_chains cc ON cc.news_analysis_id = na.id
        WHERE COALESCE(rn.is_deleted, false) = false
          AND rn.processing_status = 'processed'
          AND rn.origin_published_at >= %s::timestamptz
    """
    params: list = [start]
    if end:
        sql += " AND rn.origin_published_at < %s::timestamptz"
        params.append(end)
    sql += " ORDER BY rn.origin_published_at, na.id, cc.id"

    with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_indicator_values(
    connection,
    *,
    table: str,
    value_col: str,
    date_key_col: str,
    month_keys: list[str],
) -> dict[str, float]:
    """Return {month_key: value} for the requested months.

    Only non-null rows are returned. Identifiers are checked against
    an allowlist to prevent SQL injection.
    """
    if not month_keys:
        return {}
    _check(table, _ALLOWED_TABLES)
    _check(value_col, _ALLOWED_COLUMNS)
    _check(date_key_col, _ALLOWED_COLUMNS)

    sql = f"""
        SELECT {date_key_col} AS month_key, {value_col} AS val
        FROM {table}
        WHERE {date_key_col} = ANY(%s)
          AND {value_col} IS NOT NULL
    """
    with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (month_keys,))
        return {row["month_key"]: float(row["val"]) for row in cur.fetchall()}


def _check(name: str, allowed: frozenset[str]) -> None:
    if name not in allowed:
        raise ValueError(f"Identifier not in allowlist: {name!r}")
