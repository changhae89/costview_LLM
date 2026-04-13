"""
Guardian 과거 뉴스를 수집해 raw_news 테이블에 저장.

실행 예시:
  python history_loader/load_guardian_history.py
  python history_loader/load_guardian_history.py --from-date 2024-01-01 --to-date 2024-12-31 --days 30
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.supabase_client import create_sb, is_supabase_configured  # noqa: E402
from supabase_store import fetch_consumer_keywords_sb, upsert_history_sb  # noqa: E402

GUARDIAN_API = "https://content.guardianapis.com/search"

WAR_TERMS = [
    "war",
    "conflict",
    "invasion",
    "military",
    "attack",
    "geopolitical",
    "ukraine",
    "russia",
    "gaza",
    "middle east",
]
ITEM_TERMS = [
    "oil",
    "energy",
    "gas",
    "food",
    "wheat",
    "grain",
    "shipping",
    "fuel",
    "commodity",
    "price",
    "cost",
    "inflation",
]
UP_TERMS = ["rise", "up", "increase", "jump", "surge", "soar", "high"]
UP_PATTERNS = [
    r"\brise(s|n)?\b",
    r"\bup\b",
    r"\bincrease(s|d)?\b",
    r"\bjump(s|ed)?\b",
    r"\bsurge(s|d)?\b",
    r"\bsoar(s|ed)?\b",
    r"\bhigh(er)?\b",
]
DOWN_TERMS = ["fall", "down", "decrease", "drop", "decline", "lower", "slump"]
DOWN_PATTERNS = [
    r"\bfall(s|en)?\b",
    r"\bdown\b",
    r"\bdecrease(s|d)?\b",
    r"\bdrop(s|ped)?\b",
    r"\bdecline(s|d)?\b",
    r"\blower(ed)?\b",
    r"\bslump(s|ed)?\b",
]
WAR_PATTERNS = [rf"\b{re.escape(t)}\b" for t in WAR_TERMS]
ITEM_PATTERNS = [rf"\b{re.escape(t)}(s)?\b" for t in ITEM_TERMS]
SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+")


def load_env() -> None:
    """
    레포 루트 .env 로드.
    override=True: Windows/IDE에 빈 SUPABASE_*·API_KEY 등이 잡혀 있어도 .env 값이 적용되게 함.
    """
    here = Path(__file__).resolve().parent
    root = here.parent
    load_dotenv(here / ".env", override=True)
    load_dotenv(root / ".env", override=True)


def get_connection():
    load_env()
    if is_supabase_configured():
        raise RuntimeError(
            "SUPABASE_URL+SUPABASE_ANON_KEY 등이 설정되어 있습니다. create_sb() 와 supabase_store 를 사용하세요."
        )
    url = os.environ.get("API_KEY") or os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "API_KEY 또는 DATABASE_URL(Postgres URI), 또는 SUPABASE_URL+SUPABASE_ANON_KEY 를 설정하세요."
        )
    if "sslmode" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


def fetch_consumer_keywords(conn, limit: int = 50) -> list[str]:
    sql = """
        SELECT COALESCE(NULLIF(BTRIM(keyword_en), ''), NULLIF(BTRIM(keyword_kr), '')) AS keyword
        FROM consumer_items
        WHERE category_kr = '소비재'
          AND COALESCE(is_deleted, false) = false
          AND COALESCE(NULLIF(BTRIM(keyword_en), ''), NULLIF(BTRIM(keyword_kr), '')) IS NOT NULL
        ORDER BY COALESCE(NULLIF(BTRIM(keyword_en), ''), NULLIF(BTRIM(keyword_kr), '')) ASC
        LIMIT %s;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
    return [str(r["keyword"]).strip() for r in rows if r.get("keyword")]


def guardian_search(
    api_key: str,
    query: str,
    from_date: str,
    to_date: str,
    page: int,
    page_size: int = 50,
) -> dict[str, Any]:
    params = {
        "api-key": api_key,
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "page-size": page_size,
        "page": page,
        "order-by": "newest",
        "show-fields": "headline,trailText,bodyText",
    }
    with httpx.Client(timeout=20) as client:
        res = client.get(GUARDIAN_API, params=params)
        res.raise_for_status()
        return res.json()


def normalize_item(item: dict[str, Any], keyword: str) -> dict[str, Any] | None:
    fields = item.get("fields") or {}
    title = (fields.get("headline") or item.get("webTitle") or "").strip()
    trail = (fields.get("trailText") or "").strip()
    body = (fields.get("bodyText") or "").strip()
    content = body or trail or title
    news_url = (item.get("webUrl") or "").strip()
    published = item.get("webPublicationDate")
    if not title or not content or not news_url:
        return None
    extracted = extract_war_price_signals(title, content)
    directional = extract_directional_items(title, content)
    if not (bool(directional["increased_items"]) ^ bool(directional["decreased_items"])):
        return None
    all_keywords = sorted(set(extracted["wars"] + extracted["items"]))
    increased = None
    decreased = None
    if directional["increased_items"]:
        increased = directional["increased_items"]
    if directional["decreased_items"]:
        decreased = directional["decreased_items"]

    return {
        "title": title[:1000],
        "content": content[:12000],
        "news_url": news_url,
        "origin_published_at": published,
        "keyword": all_keywords,
        "increased_items": increased,
        "decreased_items": decreased,
    }


def is_relevant_war_price_article(title: str, content: str) -> bool:
    """
    전쟁/분쟁 + 물품/원자재 + 가격상승/하락 문맥 기사만 통과.
    """
    text = f"{title}\n{content}".lower()
    has_war = any(re.search(p, text) for p in WAR_PATTERNS)
    has_item = any(re.search(p, text) for p in ITEM_PATTERNS)
    has_up_or_down = any(re.search(p, text) for p in UP_PATTERNS + DOWN_PATTERNS)
    return has_war and has_item and has_up_or_down


def extract_war_price_signals(title: str, content: str) -> dict[str, list[str]]:
    """
    기사 텍스트에서 전쟁/물품/상승·하락 시그널 용어 추출
    """
    text = f"{title}\n{content}".lower()
    wars = sorted({t for t in WAR_TERMS if re.search(rf"\b{re.escape(t)}\b", text)})
    items = sorted({t for t in ITEM_TERMS if re.search(rf"\b{re.escape(t)}(s)?\b", text)})
    up_signals = sorted({t for t, p in zip(UP_TERMS, UP_PATTERNS) if re.search(p, text)})
    down_signals = sorted({t for t, p in zip(DOWN_TERMS, DOWN_PATTERNS) if re.search(p, text)})
    return {"wars": wars, "items": items, "up_signals": up_signals, "down_signals": down_signals}


def extract_directional_items(title: str, content: str) -> dict[str, list[str]]:
    """
    문장 단위로 item + 상승/하락 신호 동시 등장 여부를 검사해 방향별 item 분리.
    동일 item이 양쪽에 모두 나오면(모호한 경우) 양쪽에서 제거.
    """
    text = f"{title}. {content}".lower()
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]

    increased: set[str] = set()
    decreased: set[str] = set()
    up_hits = 0
    down_hits = 0

    for sent in sentences:
        has_up = any(re.search(p, sent) for p in UP_PATTERNS)
        has_down = any(re.search(p, sent) for p in DOWN_PATTERNS)
        if not (has_up or has_down):
            continue

        sent_items = {t for t in ITEM_TERMS if re.search(rf"\b{re.escape(t)}(s)?\b", sent)}
        if not sent_items:
            continue

        if has_up and not has_down:
            increased.update(sent_items)
            up_hits += 1
        elif has_down and not has_up:
            decreased.update(sent_items)
            down_hits += 1
        else:
            # 같은 문장에 상승/하락이 동시에 있으면 방향 모호: 보수적으로 제외
            continue

    overlap = increased & decreased
    if overlap:
        increased -= overlap
        decreased -= overlap

    # 한 기사에 상승/하락이 동시에 남으면 우세 방향만 유지 (동률이면 영향 범위 큰 쪽)
    if increased and decreased:
        if up_hits > down_hits:
            decreased.clear()
        elif down_hits > up_hits:
            increased.clear()
        else:
            # 동률: 아이템 수가 더 많은 방향 유지, 완전 동률이면 둘 다 제거
            if len(increased) > len(decreased):
                decreased.clear()
            elif len(decreased) > len(increased):
                increased.clear()
            else:
                increased.clear()
                decreased.clear()

    return {
        "increased_items": sorted(increased),
        "decreased_items": sorted(decreased),
    }


def upsert_history(conn, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    db_rows = []
    skipped_both = 0
    for r in rows:
        row = dict(r)
        has_increased = row.get("increased_items") is not None
        has_decreased = row.get("decreased_items") is not None
        if not (has_increased ^ has_decreased):
            skipped_both += 1
            continue
        db_rows.append(row)
    if skipped_both:
        print(f"[history] 저장 제외(상승/하락 동시): {skipped_both}건")
    if not db_rows:
        return 0
    sql = """
        INSERT INTO raw_news
            (title, content, news_url, origin_published_at, keyword, increased_items, decreased_items)
        SELECT
            %(title)s, %(content)s, %(news_url)s, %(origin_published_at)s, %(keyword)s,
            %(increased_items)s, %(decreased_items)s
        WHERE (%(increased_items)s IS NOT NULL) != (%(decreased_items)s IS NOT NULL)
        ON CONFLICT (news_url) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            origin_published_at = EXCLUDED.origin_published_at,
            keyword = (
                SELECT ARRAY(
                    SELECT DISTINCT x
                    FROM unnest(raw_news.keyword || EXCLUDED.keyword) AS t(x)
                )
            ),
            increased_items = EXCLUDED.increased_items,
            decreased_items = EXCLUDED.decreased_items,
            updated_at = NOW();
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, db_rows, page_size=100)
    conn.commit()
    return len(db_rows)


def parse_args() -> argparse.Namespace:
    now = datetime.now(timezone.utc).date()
    default_from = (now - timedelta(days=365)).isoformat()
    default_to = now.isoformat()
    p = argparse.ArgumentParser()
    p.add_argument("--from-date", default=default_from, help="YYYY-MM-DD")
    p.add_argument("--to-date", default=default_to, help="YYYY-MM-DD")
    p.add_argument("--days", type=int, default=365, help="키워드별 최대 수집 페이지 제한용(참고값)")
    p.add_argument("--max-pages", type=int, default=3, help="키워드별 최대 페이지")
    p.add_argument("--page-size", type=int, default=50, help="페이지당 기사 수 (최대 50)")
    return p.parse_args()


def main() -> None:
    load_env()
    guardian_key = os.environ["GUARDIAN_API_KEY"]
    args = parse_args()
    use_sb = is_supabase_configured()
    conn = None
    sb = None
    if use_sb:
        sb = create_sb()
        print("[history] DB: Supabase (SUPABASE_URL + SUPABASE_ANON_KEY)")
        keywords = fetch_consumer_keywords_sb(sb, limit=50)
    else:
        conn = get_connection()
        print("[history] DB: Postgres (API_KEY / DATABASE_URL)")
        keywords = fetch_consumer_keywords(conn, limit=50)

    try:
        if not keywords:
            print("[history] 소비재 키워드가 없어 종료합니다.")
            return

        print(f"[history] 기간: {args.from_date} ~ {args.to_date}")
        print(f"[history] 소비재 키워드: {len(keywords)}개")

        total_fetched = 0
        total_saved = 0

        for kw in keywords:
            keyword_rows: list[dict[str, Any]] = []
            for page in range(1, args.max_pages + 1):
                data = guardian_search(
                    api_key=guardian_key,
                    query=kw,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    page=page,
                    page_size=args.page_size,
                )
                response = data.get("response") or {}
                results = response.get("results") or []
                if not results:
                    break

                total_fetched += len(results)
                for item in results:
                    row = normalize_item(item, kw)
                    if row and is_relevant_war_price_article(row["title"], row["content"]):
                        keyword_rows.append(row)

                pages = int(response.get("pages") or 1)
                if page >= pages:
                    break

            if use_sb:
                saved = upsert_history_sb(sb, keyword_rows)
            else:
                saved = upsert_history(conn, keyword_rows)
            total_saved += saved
            print(f"[history] '{kw}' fetched={len(keyword_rows)} saved={saved}")

        print(f"[history] 완료 fetched={total_fetched} saved={total_saved}")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()

