"""Scheduled news-ingestion entrypoint for proposal data collection."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal.collectors.exa_collector import fetch_news
from proposal.common.supabase_client import create_sb, is_supabase_configured
from proposal.config import load_environment
from proposal.db.connection import get_connection
from proposal.db.fetch import fetch_consumer_keywords
from proposal.db.supabase_store import fetch_consumer_keywords_sb, upsert_news_sb
from proposal.db.upsert import upsert_news


async def main() -> None:
    """Collect news and persist it to the configured data store."""
    load_environment()
    print("[proposal] Start")

    try:
        if is_supabase_configured():
            supabase = create_sb()
            print("[proposal] DB: Supabase")
            print("[proposal] 뉴스 수집 중...")
            keyword_queries = fetch_consumer_keywords_sb(
                supabase,
                category="소비재",
                limit=30,
            )
            if keyword_queries:
                print(f"[proposal] 소비재 키워드 {len(keyword_queries)}개 로드")
            else:
                print("[proposal] 소비재 키워드 없음 - 기본 검색어 사용")

            news_list = await fetch_news(search_queries=keyword_queries or None)
            saved = upsert_news_sb(supabase, news_list)
            print(f"[proposal] Saved {saved} news rows (deduplicated)")
        else:
            connection = get_connection()
            try:
                print("[proposal] DB: Postgres")
                print("[proposal] 뉴스 수집 중...")
                keyword_queries = fetch_consumer_keywords(
                    connection,
                    category="소비재",
                    limit=30,
                )
                if keyword_queries:
                    print(f"[proposal] 소비재 키워드 {len(keyword_queries)}개 로드")
                else:
                    print("[proposal] 소비재 키워드 없음 - 기본 검색어 사용")

                news_list = await fetch_news(search_queries=keyword_queries or None)
                saved = upsert_news(connection, news_list)
                print(f"[proposal] Saved {saved} news rows (deduplicated)")
            finally:
                connection.close()

    except Exception as error:
        print(f"[proposal] Error: {error}")
        sys.exit(1)

    print("[proposal] Done")


if __name__ == "__main__":
    asyncio.run(main())
