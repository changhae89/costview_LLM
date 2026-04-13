"""Supabase read/write helpers for PRD analysis."""

from __future__ import annotations

from typing import Any


def fetch_pending_news_sb(sb: Any, limit: int = 20) -> list[dict]:
    """Fetch undeleted raw news rows without an analysis record."""
    candidate_limit = max(limit * 5, 100)
    response = (
        sb.table("raw_news")
        .select("id,news_url,title,content,origin_published_at,created_at,keyword")
        .or_("is_deleted.is.null,is_deleted.eq.false")
        .order("created_at")
        .limit(candidate_limit)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return []

    ids = [row["id"] for row in rows]
    analyzed_ids: set[str] = set()

    for index in range(0, len(ids), 100):
        partial_ids = ids[index : index + 100]
        analyses = sb.table("news_analyses").select("raw_news_id").in_("raw_news_id", partial_ids).execute()
        for analysis in analyses.data or []:
            raw_news_id = analysis.get("raw_news_id")
            if raw_news_id is not None:
                analyzed_ids.add(str(raw_news_id))

    pending_rows = [row for row in rows if str(row["id"]) not in analyzed_ids]
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
        for row in pending_rows[:limit]
    ]


def fetch_active_cost_categories_sb(sb: Any) -> list[str]:
    """Fetch active cost category codes ordered for prompt usage."""
    rows = (
        sb.table("cost_categories")
        .select("code")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    ).data or []
    return [str(row["code"]).strip() for row in rows if str(row.get("code", "")).strip()]


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


def mark_as_processed_sb(sb: Any, raw_news_id: str) -> None:
    """Best-effort status update for processed rows."""
    _update_raw_news_status_sb(
        sb,
        raw_news_id=raw_news_id,
        status="processed",
        error_message=None,
    )


def mark_as_failed_sb(sb: Any, raw_news_id: str, error_msg: str) -> None:
    """Best-effort status update for failed rows."""
    _update_raw_news_status_sb(
        sb,
        raw_news_id=raw_news_id,
        status="failed",
        error_message=error_msg[:1000],
    )


def _update_raw_news_status_sb(
    sb: Any,
    *,
    raw_news_id: str,
    status: str,
    error_message: str | None,
) -> None:
    """Attempt to update status columns, but tolerate schemas that do not define them."""
    payload = {
        "processing_status": status,
        "processing_error": error_message,
    }
    if status == "processed":
        payload["processed_at"] = "now()"

    try:
        sb.table("raw_news").update(payload).eq("id", raw_news_id).execute()
    except Exception:
        pass
