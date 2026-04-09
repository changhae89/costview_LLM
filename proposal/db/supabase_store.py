"""Supabase write helpers for proposal ingestion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _iso(value: Any) -> Any:
    """Convert datetimes to UTC ISO strings while leaving other values untouched."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


def fetch_consumer_keywords_sb(
    supabase: Any,
    category: str = "소비재",
    limit: int = 30,
) -> list[str]:
    """Fetch active consumer-item keywords from Supabase."""
    response = (
        supabase.table("consumer_items")
        .select("keyword_kr,keyword_en")
        .eq("category_kr", category)
        .or_("is_deleted.is.null,is_deleted.eq.false")
        .order("keyword_kr")
        .limit(min(limit * 3, 500))
        .execute()
    )

    seen: set[str] = set()
    keywords: list[str] = []
    for row in response.data or []:
        keyword = (row.get("keyword_en") or "").strip() or (row.get("keyword_kr") or "").strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        keywords.append(keyword)
        if len(keywords) >= limit:
            break

    return keywords


def upsert_news_sb(supabase: Any, news_list: list[dict[str, object]]) -> int:
    """Insert or update raw news rows keyed by `news_url` via PostgREST."""
    if not news_list:
        return 0

    by_url = {str(news["url"]): news for news in news_list}
    urls = list(by_url.keys())
    existing_urls: set[str] = set()

    for index in range(0, len(urls), 150):
        partial_urls = urls[index : index + 150]
        response = supabase.table("raw_news").select("news_url").in_("news_url", partial_urls).execute()
        for row in response.data or []:
            existing_urls.add(row["news_url"])

    inserts: list[dict[str, object]] = []
    for url, news in by_url.items():
        payload = {
            "title": news["title"],
            "content": news.get("content") or "",
            "origin_published_at": _iso(news.get("published_at")),
        }
        if url not in existing_urls:
            inserts.append({**payload, "news_url": url, "keyword": []})
            existing_urls.add(url)
            continue

        supabase.table("raw_news").update(payload).eq("news_url", url).execute()

    for index in range(0, len(inserts), 100):
        supabase.table("raw_news").insert(inserts[index : index + 100]).execute()

    return len(by_url)


def upsert_indicators_sb(supabase: Any, indicators: list[dict[str, object]]) -> None:
    """Upsert hourly indicator rows in Supabase."""
    if not indicators:
        return

    now = datetime.now(timezone.utc)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    for row in indicators:
        indicator_type = row["type"]
        query = (
            supabase.table("economic_indicators")
            .select("id")
            .eq("type", indicator_type)
            .gte("recorded_at", hour_start.isoformat())
            .lt("recorded_at", hour_end.isoformat())
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )

        payload = {
            "value": float(row["value"]),
            "unit": row.get("unit"),
            "source": row.get("source"),
        }
        if query.data:
            supabase.table("economic_indicators").update(payload).eq("id", query.data[0]["id"]).execute()
        else:
            supabase.table("economic_indicators").insert({"type": indicator_type, **payload}).execute()

