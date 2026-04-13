# history_loader/supabase_store.py — PostgREST, raw_news = Guardian 스키마

from __future__ import annotations

from typing import Any


def fetch_consumer_keywords_sb(sb: Any, limit: int = 50) -> list[str]:
    res = (
        sb.table("consumer_items")
        .select("keyword_kr,keyword_en")
        .eq("category_kr", "소비재")
        .or_("is_deleted.is.null,is_deleted.eq.false")
        .order("keyword_kr")
        .limit(min(limit * 3, 500))
        .execute()
    )
    seen: set[str] = set()
    out: list[str] = []
    for r in res.data or []:
        k = (r.get("keyword_en") or "").strip() or (r.get("keyword_kr") or "").strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
        if len(out) >= limit:
            break
    return out


def _iso(v: Any) -> Any:
    if v is None:
        return None
    from datetime import datetime, timezone

    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return v


def upsert_history_sb(sb: Any, rows: list[dict[str, Any]]) -> int:
    """raw_news: news_url, origin_published_at, keyword[], increased_items, decreased_items"""
    if not rows:
        return 0
    skipped_both = 0
    saved = 0
    for r in rows:
        row = dict(r)
        has_inc = row.get("increased_items") is not None
        has_dec = row.get("decreased_items") is not None
        if not (has_inc ^ has_dec):
            skipped_both += 1
            continue
        row["origin_published_at"] = _iso(row.get("origin_published_at"))
        kw_new = row.get("keyword") or []
        nu = row["news_url"]

        ex = (
            sb.table("raw_news")
            .select("keyword")
            .eq("news_url", nu)
            .limit(1)
            .execute()
        )
        if ex.data:
            old_kw = ex.data[0].get("keyword") or []
            merged = sorted({*list(old_kw), *list(kw_new)})
            payload = {
                "title": row["title"],
                "content": row["content"],
                "origin_published_at": row["origin_published_at"],
                "keyword": merged,
                "increased_items": row.get("increased_items"),
                "decreased_items": row.get("decreased_items"),
            }
            sb.table("raw_news").update(payload).eq("news_url", nu).execute()
        else:
            ins = {
                "title": row["title"],
                "content": row["content"],
                "news_url": nu,
                "origin_published_at": row["origin_published_at"],
                "keyword": list(kw_new),
                "increased_items": row.get("increased_items"),
                "decreased_items": row.get("decreased_items"),
            }
            sb.table("raw_news").insert(ins).execute()
        saved += 1
    if skipped_both:
        print(f"[history] 저장 제외(상승/하락 동시): {skipped_both}건")
    return saved
