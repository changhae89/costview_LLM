"""Scheduled analysis entrypoint for PRD news processing."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prd.common.supabase_client import create_sb, is_supabase_configured
from prd.config import get_max_batch, load_environment
from prd.db.connection import get_connection
from prd.db.fetch import fetch_pending_news
from prd.db.save import mark_as_failed, mark_as_processed, save_analysis_result
from prd.db.supabase_store import (
    fetch_pending_news_sb,
    mark_as_failed_sb,
    mark_as_processed_sb,
    save_analysis_result_sb,
)
from prd.llm.gemini_client import analyze_news


async def main() -> None:
    """Fetch pending news, analyze it with Gemini, and save the resulting chains."""
    load_environment()
    max_batch = get_max_batch()
    print("[prd] Start")
    print(f"[prd] Max batch: {max_batch}")

    use_supabase = is_supabase_configured()
    connection = None
    supabase = None

    try:
        if use_supabase:
            supabase = create_sb()
            print("[prd] DB: Supabase")
            pending_news = fetch_pending_news_sb(supabase, limit=max_batch)
        else:
            connection = get_connection()
            print("[prd] DB: Postgres")
            pending_news = fetch_pending_news(connection, limit=max_batch)

        print(f"[prd] Pending news: {len(pending_news)}")
        if not pending_news:
            print("[prd] No pending news. Done.")
            return

        success_count = 0
        failed_count = 0

        for news in pending_news:
            try:
                print("[prd] Source news:")
                print(
                    json.dumps(
                        {
                            "id": news.get("id"),
                            "title": news.get("title"),
                            "url": news.get("url"),
                            "published_at": news.get("published_at"),
                            "content_preview": (news.get("content") or "")[:1000],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                result = await analyze_news(news)
                print("[prd] LLM result:")
                print(json.dumps(result, ensure_ascii=False, indent=2))

                if use_supabase:
                    save_analysis_result_sb(supabase, news["id"], result)
                    mark_as_processed_sb(supabase, news["id"])
                else:
                    save_analysis_result(connection, news["id"], result)
                    mark_as_processed(connection, news["id"])

                print(f"[prd] OK {news['title'][:45]}...")
                success_count += 1
            except Exception as error:
                if connection is not None:
                    connection.rollback()

                try:
                    if use_supabase:
                        mark_as_failed_sb(supabase, news["id"], str(error))
                    else:
                        mark_as_failed(connection, news["id"], str(error))
                except Exception as mark_error:
                    if connection is not None:
                        connection.rollback()
                    print(
                        f"[prd] FAIL {news['title'][:45]}... - {error} "
                        f"(mark failed also failed: {mark_error})"
                    )
                else:
                    print(f"[prd] FAIL {news['title'][:45]}... - {error}")

                failed_count += 1

        print(f"[prd] Done - success: {success_count}, failed: {failed_count}")
    except Exception as error:
        print(f"[prd] Fatal error: {error}")
        sys.exit(1)
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    asyncio.run(main())
