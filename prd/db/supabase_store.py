"""Supabase read/write helpers for PRD analysis."""

from __future__ import annotations

from typing import Any


def count_pending_news_sb(sb: Any) -> int:
    """Count rows that fetch_pending_news_sb would return (same filters)."""
    resp = (
        sb.table("raw_news")
        .select("id", count="exact", head=True)
        .or_("is_deleted.is.null,is_deleted.eq.false")
        .is_("processing_status", "null")
        .execute()
    )
    return int(resp.count or 0)


def fetch_pending_news_sb(sb: Any, *, limit: int = 10) -> list[dict]:
    """Fetch unprocessed raw news rows up to limit (processing_status IS NULL, not deleted).

    Paginates in batches of 1000 to work around Supabase server-side row limit.
    """
    PAGE_SIZE = 1000
    collected: list[dict] = []
    offset = 0

    while len(collected) < limit:
        fetch_count = min(PAGE_SIZE, limit - len(collected))
        rows = (
            sb.table("raw_news")
            .select("id,news_url,title,content,origin_published_at,created_at,keyword")
            .or_("is_deleted.is.null,is_deleted.eq.false")
            .is_("processing_status", "null")
            .order("origin_published_at")
            .range(offset, offset + fetch_count - 1)
            .execute()
        ).data or []

        if not rows:
            break

        collected.extend(rows)
        offset += len(rows)

        if len(rows) < fetch_count:
            break

    return [
        {
            "id": row["id"],
            "url": row["news_url"],
            "title": row["title"],
            "source": None,
            "content": row.get("content"),
            "published_at": row.get("origin_published_at"),
            "created_at": row.get("created_at"),
            "keyword": row.get("keyword") or [],
        }
        for row in collected
    ]


def fetch_active_cost_categories_sb(sb: Any) -> list[dict]:
    """Fetch active cost categories with labels and keywords for prompt usage."""
    rows = (
        sb.table("cost_categories")
        .select("code, name_ko, keywords")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    ).data or []
    return [row for row in rows if str(row.get("code", "")).strip()]


def fetch_analysis_history_sb(
    sb: Any,
    *,
    current_news_id: str,
    keywords: list[str] | None,
    published_at: str | None,
    limit: int = 5,
) -> list[dict]:
    """Fetch analyzed historical context using news_analyses + causal_chains."""
    safe_keywords = [str(item).strip() for item in (keywords or []) if str(item).strip()]
    candidate_limit = max(limit * 5, 20)
    rows = (
        sb.table("raw_news")
        .select(
            "id,title,origin_published_at,keyword,"
            "news_analyses(id,summary,reliability,related_indicators,"
            "causal_chains(category,direction,magnitude,change_pct_min,change_pct_max,monthly_impact))"
        )
        .neq("id", current_news_id)
        .or_("is_deleted.is.null,is_deleted.eq.false")
        .order("origin_published_at", desc=True)
        .limit(candidate_limit)
        .execute()
    ).data or []

    out: list[dict] = []
    for row in rows:
        row_keywords = [str(item).strip() for item in (row.get("keyword") or []) if str(item).strip()]
        if safe_keywords and not set(row_keywords).intersection(safe_keywords):
            continue
        if published_at and row.get("origin_published_at") and row["origin_published_at"] > published_at:
            continue
        analyses = row.get("news_analyses") or []
        if not analyses:
            continue
        analysis = analyses[0]
        out.append(
            {
                "raw_news_id": row["id"],
                "title": row.get("title"),
                "published_at": row.get("origin_published_at"),
                "analysis_id": analysis.get("id"),
                "summary": analysis.get("summary", ""),
                "reliability": float(analysis.get("reliability") or 0),
                "related_indicators": analysis.get("related_indicators") or [],
                "effects": analysis.get("causal_chains") or [],
            }
        )
        if len(out) >= limit:
            break
    return out


def save_analysis_result_sb(sb: Any, raw_news_id: str, result: dict) -> None:
    """Insert one analysis row and its causal effect rows via Supabase."""
    inserted = (
        sb.table("news_analyses")
        .insert(
            {
                "raw_news_id": raw_news_id,
                "summary": result.get("summary", ""),
                "reliability": float(result.get("reliability", 0.85)),
                "related_indicators": result.get("related_indicators") or [],
                "reliability_reason": result.get("reliability_reason") or "",
                "time_horizon": result.get("time_horizon"),
                "effect_chain": result.get("effect_chain") or [],
                "buffer": result.get("buffer") or "",
                "leading_indicator": result.get("leading_indicator"),
                "geo_scope": result.get("geo_scope"),
            }
        )
        .execute()
    )
    rows = inserted.data or []
    if not rows or "id" not in rows[0]:
        raise RuntimeError("news_analyses insert did not return id")

    analysis_id = str(rows[0]["id"])
    try:
        for effect in result.get("effects", []):
            sb.table("causal_chains").insert(
                {
                    "news_analysis_id": analysis_id,
                    "event": result.get("event", ""),
                    "mechanism": result.get("mechanism", ""),
                    "category": effect.get("category", ""),
                    "direction": effect.get("direction", "neutral"),
                    "magnitude": effect.get("magnitude", "low"),
                    "change_pct_min": effect.get("change_pct_min"),
                    "change_pct_max": effect.get("change_pct_max"),
                    "monthly_impact": effect.get("monthly_impact"),
                }
            ).execute()
    except Exception:
        sb.table("news_analyses").delete().eq("id", analysis_id).execute()
        raise


def fetch_indicators_by_date_sb(sb: Any, *, reference_date: str) -> dict:
    """Fetch 12-month monthly series of economic indicators up to reference_date."""
    from datetime import date as _date, timedelta

    ref = _date.fromisoformat(reference_date[:10])
    # 11개월 전 월의 1일 계산
    start = ref.replace(day=1)
    for _ in range(11):
        start = (start - timedelta(days=1)).replace(day=1)
    start_month_str = start.isoformat()
    end_month_str = ref.replace(day=1).isoformat()
    start_ref_month = start.isoformat()[:7]
    end_ref_month = ref.isoformat()[:7]

    def _monthly(table: str, date_col: str, value_col: str) -> list[tuple[str, float]]:
        rows = (
            sb.table(table)
            .select(f"{date_col},{value_col}")
            .gte(date_col, start_month_str)
            .lte(date_col, end_month_str)
            .not_.is_(value_col, "null")
            .order(date_col)
            .execute()
        ).data or []
        return [(r[date_col][:7], float(r[value_col])) for r in rows]

    def _monthly_str(table: str, date_col: str, value_col: str) -> list[tuple[str, float]]:
        rows = (
            sb.table(table)
            .select(f"{date_col},{value_col}")
            .gte(date_col, start_ref_month)
            .lte(date_col, end_ref_month)
            .not_.is_(value_col, "null")
            .order(date_col)
            .execute()
        ).data or []
        return [(r[date_col][:7], float(r[value_col])) for r in rows]

    def _daily_to_monthly(table: str, date_col: str, value_col: str) -> list[tuple[str, float]]:
        rows = (
            sb.table(table)
            .select(f"{date_col},{value_col}")
            .gte(date_col, start_month_str)
            .lte(date_col, reference_date)
            .not_.is_(value_col, "null")
            .order(date_col)
            .execute()
        ).data or []
        by_month: dict[str, list[float]] = {}
        for r in rows:
            m = r[date_col][:7]
            by_month.setdefault(m, []).append(float(r[value_col]))
        return [(m, sum(v) / len(v)) for m, v in sorted(by_month.items())]

    return {
        "reference_date": reference_date,
        "krw_usd_rate": _daily_to_monthly("indicator_ecos_daily_logs", "reference_date", "krw_usd_rate"),
        "wti": _monthly("indicator_ecos_monthly_logs", "reference_date", "import_price_crude_oil"),
        "cpi_total": _monthly("indicator_kosis_monthly_logs", "reference_date", "cpi_total"),
        "gpr": _monthly("indicator_gpr_monthly_logs", "reference_date", "gpr_original"),
        "fred_wti": _daily_to_monthly("indicator_fred_daily_logs", "reference_date", "fred_wti"),
        "fred_cpi": _monthly_str("indicator_fred_monthly_logs", "reference_month", "fred_cpi"),
    }


def mark_as_processing_sb(sb: Any, raw_news_id: str) -> None:
    """Mark a raw news row as in-progress before LLM analysis."""
    sb.table("raw_news").update({
        "processing_status": "processing",
    }).eq("id", raw_news_id).execute()


def mark_as_processed_sb(sb: Any, raw_news_id: str) -> None:
    """Mark a raw news row as successfully processed."""
    sb.table("raw_news").update({
        "processing_status": "processed",
        "processing_error": None,
        "processed_at": "now()",
    }).eq("id", raw_news_id).execute()


def mark_as_skipped_sb(sb: Any, raw_news_id: str) -> None:
    """Mark a raw news row as skipped (LLM returned empty effects)."""
    sb.table("raw_news").update({
        "processing_status": "skipped",
        "processing_error": None,
        "processed_at": "now()",
    }).eq("id", raw_news_id).execute()


def mark_as_failed_sb(sb: Any, raw_news_id: str, error_msg: str) -> None:
    """Mark a raw news row as failed and increment retry_count."""
    current = (
        sb.table("raw_news")
        .select("retry_count")
        .eq("id", raw_news_id)
        .single()
        .execute()
    ).data or {}
    retry_count = (current.get("retry_count") or 0) + 1
    sb.table("raw_news").update({
        "processing_status": "failed",
        "processing_error": error_msg[:1000],
        "retry_count": retry_count,
    }).eq("id", raw_news_id).execute()
