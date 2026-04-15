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

from prd.config import get_concurrency, get_max_batch, load_environment
from prd.db.factory import create_repository
from prd.llm.graph.news_pipeline_graph import analyze_news

# ── 실행 파라미터 ─────────────────────────────────────────────
MAX_BATCH = 1000   # 한 번에 가져올 뉴스 수 (env: PRD_MAX_BATCH 로 override 가능)
CONCURRENCY = 1   # 동시에 LLM 호출할 수 (1 = 순차, 5 = 5건 병렬)
# ─────────────────────────────────────────────────────────────


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


async def _process_one(news: dict, repo, allowed_categories: list[dict]) -> None:
    title_preview = (news.get("title") or "")[:45]
    news_id = news["id"]

    try:
        repo.mark_as_processing(news_id)

        graph_news = dict(news)
        graph_news["allowed_categories"] = allowed_categories
        graph_news["_repo"] = repo

        result = await analyze_news(graph_news)
        trace = result.pop("_trace", [])
        skip = result.pop("_skip", False)
        _print_trace(trace)
        if skip:
            repo.mark_as_skipped(news_id)
            _log(f"skipped news_id={news_id} title={title_preview!r} (empty effects)")
        else:
            _log(f"LLM result for news_id={news_id}")
            _safe_print_json(result)
            repo.save_analysis_result(news_id, result)
            repo.mark_as_processed(news_id)
            _log(f"processed news_id={news_id} title={title_preview!r}")
    except Exception as error:
        try:
            repo.rollback()
        except Exception:
            pass
        try:
            repo.mark_as_failed(news_id, str(error))
        except Exception as mark_error:
            try:
                repo.rollback()
            except Exception:
                pass
            _log(
                f"failed news_id={news_id} title={title_preview!r} "
                f"error={error} mark_failed_error={mark_error}"
            )
        else:
            _log(f"failed news_id={news_id} title={title_preview!r} error={error}")
        raise


async def main() -> None:
    load_environment()
    max_batch = MAX_BATCH or get_max_batch()
    concurrency = CONCURRENCY or get_concurrency()

    _log("start")
    _log(f"Max batch: {max_batch} / Concurrency: {concurrency}")

    repo = create_repository()
    backend = type(repo).__name__
    _log(f"DB: {backend}")

    try:
        allowed_categories = repo.fetch_active_cost_categories()
        _log(f"Allowed categories: {[c['code'] for c in allowed_categories]}")

        pending_news = repo.fetch_pending_news(limit=max_batch)
        _log(f"Pending: {len(pending_news)}건")

        if not pending_news:
            _log("처리할 뉴스 없음. 종료.")
            return

        success_count = 0
        failed_count = 0
        semaphore = asyncio.Semaphore(concurrency)

        async def _bounded(index: int, news: dict) -> bool:
            async with semaphore:
                started_at = time.perf_counter()
                _log(f"[{index}/{len(pending_news)}] processing...")
                try:
                    await _process_one(news, repo, allowed_categories)
                    return True
                except Exception:
                    return False
                finally:
                    elapsed = time.perf_counter() - started_at
                    _log(f"[{index}/{len(pending_news)}] elapsed={elapsed:.2f}s")

        results = await asyncio.gather(
            *[_bounded(i, news) for i, news in enumerate(pending_news, start=1)],
            return_exceptions=False,
        )
        success_count = sum(1 for r in results if r)
        failed_count = sum(1 for r in results if not r)

        _log(f"complete success={success_count} fail={failed_count}")
    except Exception as error:
        _log(f"Fatal error: {error}")
        sys.exit(1)
    finally:
        repo.close()


if __name__ == "__main__":
    asyncio.run(main())
