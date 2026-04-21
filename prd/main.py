"""
PRD 뉴스 분석 실행 엔트리포인트
================================
미처리 raw_news를 Gemini LLM으로 분석하여
news_analyses + causal_chains 테이블에 저장한다.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prd.config import get_concurrency, get_max_batch, load_environment
from prd.db.factory import create_repository
from prd.llm.graph.news_pipeline_graph import analyze_news

# ── 실행 파라미터 ─────────────────────────────────────────────
MAX_BATCH   = 10000  # 전체 처리할 최대 뉴스 수 (env: PRD_MAX_BATCH 로 override 가능)
CONCURRENCY = 5      # 동시에 LLM 호출할 수 (1 = 순차, 5 = 5건 병렬)
CHUNK_SIZE  = 100     # 한 번에 DB에서 가져올 건수
# ─────────────────────────────────────────────────────────────


class _TeeStream:
    def __init__(self, *streams) -> None:
        self._streams = streams
        self.encoding = getattr(streams[0], "encoding", "utf-8") if streams else "utf-8"

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(getattr(stream, "isatty", lambda: False)() for stream in self._streams)


def _log(message: str) -> None:
    print(f"[prd] {message}")


def _get_runtime_int(env_name: str, default: int) -> int:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


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
        elapsed = item.get("elapsed")
        elapsed_str = f"{elapsed:.2f}s" if elapsed is not None else "-"
        _log(f"| {index} | {node} | llm={llm} | {elapsed_str} | {detail} |")


def _llm_timing(trace: list[dict] | None) -> str:
    items = trace or []
    llm1 = next((f"{t['elapsed']:.1f}s" for t in items if t.get("node") == "summarize" and "elapsed" in t), None)
    llm2 = next((f"{t['elapsed']:.1f}s" for t in items if t.get("node") == "extract_causal" and "elapsed" in t), None)
    parts = []
    if llm1:
        parts.append(f"LLM1={llm1}")
    if llm2:
        parts.append(f"LLM2={llm2}")
    return " ".join(parts)


def _configure_run_logging() -> Path:
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"prd_run_{timestamp}.log"
    log_file = log_path.open("w", encoding="utf-8", buffering=1)
    sys.stdout = _TeeStream(sys.stdout, log_file)
    sys.stderr = _TeeStream(sys.stderr, log_file)
    return log_path


async def _process_one(news: dict, repo, allowed_categories: list[dict]) -> None:
    title_preview = (news.get("title") or "")[:45]
    news_id = news["id"]

    try:
        await asyncio.to_thread(repo.mark_as_processing, news_id)

        graph_news = dict(news)
        graph_news["allowed_categories"] = allowed_categories
        graph_news["_repo"] = repo

        result = await analyze_news(graph_news)
        trace = result.pop("_trace", [])
        skip = result.pop("_skip", False)
        _print_trace(trace)
        timing = _llm_timing(trace)
        if skip:
            await asyncio.to_thread(repo.mark_as_skipped, news_id)
            _log(f"skipped news_id={news_id} title={title_preview!r} {timing}")
        else:
            _log(f"LLM result for news_id={news_id}")
            _safe_print_json(result)
            await asyncio.to_thread(repo.save_analysis_result, news_id, result)
            await asyncio.to_thread(repo.mark_as_processed, news_id)
            _log(f"processed news_id={news_id} title={title_preview!r} {timing}")
    except Exception as error:
        try:
            await asyncio.to_thread(repo.rollback)
        except Exception:
            pass
        try:
            await asyncio.to_thread(repo.mark_as_failed, news_id, str(error))
        except Exception as mark_error:
            try:
                await asyncio.to_thread(repo.rollback)

            except Exception:
                pass
            _log(
                f"failed news_id={news_id} title={title_preview!r} "
                f"error={error} mark_failed_error={mark_error}"
            )
        else:
            _log(f"failed news_id={news_id} title={title_preview!r} error={error}")
        traceback.print_exc()
        raise


async def main() -> None:
    log_path = _configure_run_logging()
    load_environment()
    max_batch = _get_runtime_int("PRD_MAX_BATCH", MAX_BATCH or get_max_batch())
    concurrency = _get_runtime_int("PRD_CONCURRENCY", CONCURRENCY or get_concurrency())
    chunk_size = _get_runtime_int("PRD_CHUNK_SIZE", CHUNK_SIZE)

    _log("start")
    _log(f"Log file: {log_path}")
    _log(f"Max batch: {max_batch} / Concurrency: {concurrency} / Chunk size: {chunk_size}")

    repo = create_repository()
    backend = type(repo).__name__
    _log(f"DB: {backend}")

    try:
        allowed_categories = await asyncio.to_thread(repo.fetch_active_cost_categories)
        _log(f"Allowed categories: {[c['code'] for c in allowed_categories]}")

        pending_count = await asyncio.to_thread(repo.count_pending_news)
        progress_total = min(pending_count, max_batch)
        if progress_total < pending_count:
            _log(f"Pending queue: {pending_count} (this run: {progress_total} via PRD_MAX_BATCH)")
        else:
            _log(f"Pending queue: {pending_count}")

        total_processed = 0
        success_count = 0
        failed_count = 0
        semaphore = asyncio.Semaphore(concurrency)

        async def _bounded(batch_index: int, total_index: int, batch_size: int, news: dict) -> bool:
            async with semaphore:
                started_at = time.perf_counter()
                _log(f"[{total_index}/{progress_total}] processing... (batch {batch_index}/{batch_size})")
                try:
                    await _process_one(news, repo, allowed_categories)
                    return True
                except Exception:
                    return False
                finally:
                    elapsed = time.perf_counter() - started_at
                    _log(f"[{total_index}/{progress_total}] elapsed={elapsed:.2f}s")

        while total_processed < max_batch:
            remaining = max_batch - total_processed
            batch_limit = min(chunk_size, remaining)
            pending_news = await asyncio.to_thread(repo.fetch_pending_news, limit=batch_limit)

            if not pending_news:
                if total_processed == 0:
                    _log("처리할 뉴스 없음. 종료.")
                else:
                    _log("더 이상 처리할 뉴스 없음. 종료.")
                break

            batch_size = len(pending_news)
            _log(
                f"Fetched batch size={batch_size} "
                f"(processed={total_processed}/{progress_total}, remaining_cap={remaining})"
            )

            results = await asyncio.gather(
                *[
                    _bounded(
                        batch_index=i,
                        total_index=total_processed + i,
                        batch_size=batch_size,
                        news=news,
                    )
                    for i, news in enumerate(pending_news, start=1)
                ],
                return_exceptions=False,
            )

            success_count += sum(1 for r in results if r)
            failed_count += sum(1 for r in results if not r)
            total_processed += batch_size

        _log(f"complete success={success_count} fail={failed_count}")
    except Exception as error:
        _log(f"Fatal error: {error}")
        sys.exit(1)
    finally:
        repo.close()


if __name__ == "__main__":
    asyncio.run(main())
