from fastapi import APIRouter

from db import get_conn

router = APIRouter()


def _rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _safe_rows(conn, table: str, order_col: str, limit: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT *
            FROM {table}
            ORDER BY {order_col} DESC
            LIMIT %s
            """,
            (limit,),
        )
        return _rows(cur)


def _normalize_gpr(row: dict) -> dict:
    if "AI_GPR_Index" in row and row.get("ai_gpr_index") is None:
        row["ai_gpr_index"] = row.get("AI_GPR_Index")
    return row


def _merge_daily(conn) -> list[dict]:
    datasets = [
        _safe_rows(conn, "indicator_gpr_daily_logs", "reference_date", 2000),
        _safe_rows(conn, "indicator_ecos_daily_logs", "reference_date", 2000),
        _safe_rows(conn, "indicator_fred_daily_logs", "reference_date", 2000),
    ]
    merged: dict[str, dict] = {}
    for rows in datasets:
        for item in rows:
            date_key = str(item.get("reference_date") or "")
            if not date_key:
                continue
            merged.setdefault(date_key, {"reference_date": item.get("reference_date")})
            merged[date_key].update(_normalize_gpr(item))
    return sorted(merged.values(), key=lambda r: str(r.get("reference_date") or ""))


def _merge_monthly(conn) -> list[dict]:
    datasets = [
        (_safe_rows(conn, "indicator_gpr_monthly_logs", "reference_date", 120), "reference_date"),
        (_safe_rows(conn, "indicator_ecos_monthly_logs", "reference_date", 120), "reference_date"),
        (_safe_rows(conn, "indicator_fred_monthly_logs", "reference_month", 120), "reference_month"),
        (_safe_rows(conn, "indicator_kosis_monthly_logs", "reference_date", 120), "reference_date"),
    ]
    merged: dict[str, dict] = {}
    for rows, date_field in datasets:
        for item in rows:
            raw_date = item.get(date_field)
            if not raw_date:
                continue
            month_key = str(raw_date)[:7]
            normalized_date = str(raw_date)[:10] if len(str(raw_date)) >= 10 else f"{month_key}-01"
            merged.setdefault(month_key, {"reference_date": normalized_date})
            row = dict(item)
            if date_field == "reference_month":
                row["reference_date"] = normalized_date
            merged[month_key].update(_normalize_gpr(row))
    return sorted(merged.values(), key=lambda r: str(r.get("reference_date") or ""))


def _nth_non_null_value(rows: list[dict], key: str, nth: int = 0):
    seen = 0
    for row in reversed(rows):
        value = row.get(key)
        if value is None or value == "":
            continue
        if seen == nth:
            return value
        seen += 1
    return None


def _nth_non_null_row(rows: list[dict], key: str, nth: int = 0) -> dict | None:
    seen = 0
    for row in reversed(rows):
        value = row.get(key)
        if value is None or value == "":
            continue
        if seen == nth:
            return row
        seen += 1
    return None


@router.get("/dashboard-metrics")
def get_dashboard_metrics():
    metric_keys = ["ai_gpr_index", "krw_usd_rate", "fred_wti", "cpi_total", "fred_treasury_10y"]
    with get_conn() as conn:
        rows = sorted([*_merge_monthly(conn), *_merge_daily(conn)], key=lambda r: str(r.get("reference_date") or ""))

    latest_row = rows[-1] if rows else {}
    prev_row = rows[-2] if len(rows) > 1 else {}
    latest_metrics = {key: _nth_non_null_value(rows, key, 0) for key in metric_keys}
    prev_metrics = {key: _nth_non_null_value(rows, key, 1) for key in metric_keys}
    latest_dates = {
        key: (_nth_non_null_row(rows, key, 0) or {}).get("reference_date", "")
        for key in metric_keys
    }
    prev_dates = {
        key: (_nth_non_null_row(rows, key, 1) or {}).get("reference_date", "")
        for key in metric_keys
    }

    return {
        "latest": {
            **latest_row,
            **latest_metrics,
            "dates": latest_dates,
            "ai_gpr_index": latest_metrics.get("ai_gpr_index") or latest_row.get("ai_gpr_index"),
            "reference_date": latest_row.get("reference_date"),
        },
        "prev": {
            **prev_row,
            **prev_metrics,
            "dates": prev_dates,
            "ai_gpr_index": prev_metrics.get("ai_gpr_index") or prev_row.get("ai_gpr_index"),
            "reference_date": prev_row.get("reference_date"),
        },
    }


@router.get("/causal-chains")
def list_causal_chains():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  cc.category,
                  cc.direction,
                  cc.magnitude,
                  cc.change_pct_min,
                  cc.change_pct_max,
                  json_build_object(
                    'reliability', na.reliability,
                    'created_at', na.created_at
                  ) AS news_analyses
                FROM causal_chains cc
                JOIN news_analyses na ON na.id = cc.news_analysis_id
                WHERE cc.direction <> 'neutral'
                  AND na.reliability >= 0.3
                """
            )
            return _rows(cur)


@router.get("/news")
def list_news(
    offset: int = 0,
    limit: int = 50,
    query: str = "",
    dir_filter: str = "",
    cat_filter: str = "",
    sort_asc: bool = False,
):
    where = ["na.reliability >= %s", "rn.is_deleted = false"]
    params: list[object] = [0.3]

    if query:
        where.append("na.summary ILIKE %s")
        params.append(f"%{query}%")
    if dir_filter:
        where.append(
            """
            EXISTS (
              SELECT 1 FROM causal_chains ccf
              WHERE ccf.news_analysis_id = na.id AND ccf.direction = %s
            )
            """
        )
        params.append(dir_filter)
    if cat_filter:
        if cat_filter == "__high__":
            where.append("na.reliability >= %s")
            params.append(0.8)
        else:
            where.append(
                """
                EXISTS (
                  SELECT 1 FROM causal_chains ccf
                  WHERE ccf.news_analysis_id = na.id AND ccf.category = %s
                )
                """
            )
            params.append(cat_filter)

    where_sql = " AND ".join(where)
    order_sql = "ASC" if sort_asc else "DESC"
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM news_analyses na
                JOIN raw_news rn ON rn.id = na.raw_news_id
                WHERE {where_sql}
                """,
                params,
            )
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT
                  na.id,
                  na.summary,
                  na.reliability,
                  na.created_at,
                  json_build_object(
                    'id', rn.id,
                    'title', rn.title,
                    'keyword', rn.keyword,
                    'increased_items', rn.increased_items,
                    'decreased_items', rn.decreased_items,
                    'is_deleted', rn.is_deleted,
                    'origin_published_at', rn.origin_published_at,
                    'news_url', rn.news_url
                  ) AS raw_news,
                  COALESCE(
                    json_agg(
                      json_build_object(
                        'category', cc.category,
                        'direction', cc.direction,
                        'magnitude', cc.magnitude
                      )
                    ) FILTER (WHERE cc.id IS NOT NULL),
                    '[]'::json
                  ) AS causal_chains
                FROM news_analyses na
                JOIN raw_news rn ON rn.id = na.raw_news_id
                LEFT JOIN causal_chains cc ON cc.news_analysis_id = na.id
                WHERE {where_sql}
                GROUP BY na.id, rn.id
                ORDER BY COALESCE(rn.origin_published_at, na.created_at) {order_sql}
                LIMIT %s OFFSET %s
                """,
                [*params, safe_limit, safe_offset],
            )
            return {"data": _rows(cur), "count": total}


@router.get("/predictions")
def list_predictions():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  cc.id,
                  cc.category,
                  cc.direction,
                  cc.magnitude,
                  cc.change_pct_min,
                  cc.change_pct_max,
                  cc.event,
                  cc.mechanism,
                  cc.monthly_impact,
                  json_build_object(
                    'id', na.id,
                    'summary', na.summary,
                    'reliability', na.reliability,
                    'created_at', na.created_at,
                    'related_indicators', na.related_indicators,
                    'reliability_reason', na.reliability_reason,
                    'time_horizon', na.time_horizon,
                    'leading_indicator', na.leading_indicator,
                    'buffer', na.buffer,
                    'geo_scope', na.geo_scope,
                    'raw_news', json_build_object(
                      'id', rn.id,
                      'title', rn.title,
                      'keyword', rn.keyword,
                      'origin_published_at', rn.origin_published_at,
                      'news_url', rn.news_url
                    )
                  ) AS news_analyses
                FROM causal_chains cc
                JOIN news_analyses na ON na.id = cc.news_analysis_id
                LEFT JOIN raw_news rn ON rn.id = na.raw_news_id
                WHERE na.reliability >= 0.3
                ORDER BY cc.id DESC
                LIMIT 2000
                """
            )
            rows = _rows(cur)

    grouped: dict[str, dict] = {}
    for row in rows:
        news = row.get("news_analyses")
        if not news:
            continue
        key = f"{row.get('category')}_{row.get('direction')}"
        if key not in grouped:
            grouped[key] = {**row, "news_analyses": [news]}
            continue
        if not any(item.get("id") == news.get("id") for item in grouped[key]["news_analyses"]):
            grouped[key]["news_analyses"].append(news)

    result = []
    for item in grouped.values():
        item["news_analyses"].sort(key=lambda n: str((n.get("raw_news") or {}).get("origin_published_at") or n.get("created_at") or ""), reverse=True)
        result.append(item)
    return sorted(
        result,
        key=lambda item: str(((item.get("news_analyses") or [{}])[0].get("raw_news") or {}).get("origin_published_at") or (item.get("news_analyses") or [{}])[0].get("created_at") or ""),
        reverse=True,
    )


@router.get("/indicators/daily")
def list_daily_indicators():
    with get_conn() as conn:
        return _merge_daily(conn)


@router.get("/indicators/monthly")
def list_monthly_indicators():
    with get_conn() as conn:
        return _merge_monthly(conn)
