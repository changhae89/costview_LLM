"""Supabase read/write helpers for PRD analysis."""

from __future__ import annotations

from typing import Any


def fetch_pending_news_sb(sb: Any, limit: int = 20) -> list[dict]:
    """Fetch undeleted raw news rows without an analysis record."""
    candidate_limit = max(limit * 5, 100)
    response = (
        sb.table("raw_news")
        .select("id,news_url,title,content,origin_published_at,created_at")
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
        }
        for row in pending_rows[:limit]
    ]


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

