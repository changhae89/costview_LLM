"""
PRD 뉴스 분석 실행 엔트리포인트
================================
미처리 raw_news를 Gemini LLM으로 분석하여
news_analyses + causal_chains 테이블에 저장한다.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prd.common.supabase_client import create_sb, is_supabase_configured
from prd.config import get_max_batch, load_environment
from prd.db.connection import get_connection
from prd.db.fetch import fetch_active_cost_categories, fetch_pending_news
from prd.db.save import mark_as_failed, mark_as_processed, save_analysis_result
from prd.db.supabase_store import (
    fetch_active_cost_categories_sb,
    fetch_pending_news_sb,
    mark_as_failed_sb,
    mark_as_processed_sb,
    save_analysis_result_sb,
)
from prd.llm.gemini_client import analyze_news


def _log(message: str) -> None:
    print(f"[prd] {message}")


def _safe_print_json(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    encoding = (sys.stdout.encoding or "utf-8").lower()
    try:
        text.encode(encoding)
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


def _print_trace(trace: list[dict] | None) -> None:
    items = trace or []
    if not items:
        return

    _log("chain graph")
    for index, item in enumerate(items, start=1):
        node = item.get("node", "")
        llm = "yes" if item.get("llm") else "no"
        detail = item.get("detail", "")
        _log(f"| {index} | {node} | llm={llm} | {detail} |")


def _fetch_pending(supabase, connection, limit: int) -> list[dict]:
    if supabase:
        return fetch_pending_news_sb(supabase, limit=limit)
    return fetch_pending_news(connection, limit=limit)


def _fetch_allowed_categories(supabase, connection) -> list[str]:
    if supabase:
        return fetch_active_cost_categories_sb(supabase)
    return fetch_active_cost_categories(connection)


def _save_result(supabase, connection, news_id: str, result: dict) -> None:
    if supabase:
        save_analysis_result_sb(supabase, news_id, result)
        mark_as_processed_sb(supabase, news_id)
    else:
        save_analysis_result(connection, news_id, result)
        mark_as_processed(connection, news_id)


def _mark_failed(supabase, connection, news_id: str, error_msg: str) -> None:
    if supabase:
        mark_as_failed_sb(supabase, news_id, error_msg)
    else:
        mark_as_failed(connection, news_id, error_msg)


async def _process_one(news: dict, supabase, connection, allowed_categories: list[str]) -> None:
    title_preview = (news.get("title") or "")[:45]
    news_id = news["id"]

    try:
        graph_news = dict(news)
        graph_news["allowed_categories"] = allowed_categories
        if supabase:
            graph_news["_history_backend"] = "supabase"
            graph_news["_sb"] = supabase
        else:
            graph_news["_history_backend"] = "postgres"
            graph_news["_conn"] = connection

        result = await analyze_news(graph_news)
        trace = result.pop("_trace", [])
        _print_trace(trace)
        _log(f"LLM result for news_id={news_id}")
        _safe_print_json(result)
        _save_result(supabase, connection, news_id, result)
        _log(f"processed news_id={news_id} title={title_preview!r}")
    except Exception as error:
        if connection is not None:
            connection.rollback()
        try:
            _mark_failed(supabase, connection, news_id, str(error))
        except Exception as mark_error:
            if connection is not None:
                connection.rollback()
            _log(
                f"failed news_id={news_id} title={title_preview!r} "
                f"error={error} mark_failed_error={mark_error}"
            )
        else:
            _log(f"failed news_id={news_id} title={title_preview!r} error={error}")
        raise


async def main() -> None:
    load_environment()
    max_batch = get_max_batch()

    _log("start")
    _log(f"Max batch: {max_batch}")

    use_supabase = is_supabase_configured()
    connection = None
    supabase = None

    try:
        if use_supabase:
            supabase = create_sb()
            _log("DB: Supabase")
        else:
            connection = get_connection()
            _log("DB: PostgreSQL")

        allowed_categories = _fetch_allowed_categories(supabase, connection)
        _log(f"Allowed categories: {allowed_categories}")

        pending_news = _fetch_pending(supabase, connection, limit=max_batch)
        _log(f"Pending: {len(pending_news)}건")

        if not pending_news:
            _log("처리할 뉴스 없음. 종료.")
            return

        success_count = 0
        failed_count = 0

        for index, news in enumerate(pending_news, start=1):
            started_at = time.perf_counter()
            _log(f"[{index}/{len(pending_news)}] processing...")
            try:
                await _process_one(news, supabase, connection, allowed_categories)
                success_count += 1
            except Exception:
                failed_count += 1
            finally:
                elapsed = time.perf_counter() - started_at
                _log(f"[{index}/{len(pending_news)}] elapsed={elapsed:.2f}s")

        _log(f"complete success={success_count} fail={failed_count}")
    except Exception as error:
        _log(f"Fatal error: {error}")
        sys.exit(1)
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    asyncio.run(main())
