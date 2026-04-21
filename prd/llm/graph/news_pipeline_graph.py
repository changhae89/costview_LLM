from __future__ import annotations

import asyncio
import re
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from prd.llm.chains.causal_normalizer import (
    normalize_causal,
    parse_causal_json,
    validate_causal_result,
)
from prd.llm.chains.category_registry import CATEGORY_FALLBACK_MAP, build_english_fallback_map
from prd.llm.chains.history_builder import build_history_context
from prd.llm.chains.llm_runner import run_causal_chain, run_summary_chain

from prd.constants.keywords import (
    _ENGLISH_DIRECT_COST_KEYWORDS,
    _ENGLISH_ECONOMIC_KEYWORDS_STRICT,
    _ENGLISH_MARKET_TOPIC_KEYWORDS,
    _KOREAN_DIRECT_COST_KEYWORDS,
    _KOREAN_ECONOMIC_KEYWORDS,
    _LIVE_BLOG_TITLE_PATTERNS,
    _SUMMARY_GROUNDING_KEYWORDS,
)
from pprint import pprint  # Added dummy or just keep it clean





class NewsState(TypedDict, total=False):
    news: dict[str, Any]
    summary: str
    history_context: str
    indicator_context: str
    causal_raw: str
    causal: dict[str, Any]
    result: dict[str, Any]
    attempts: int
    error: str
    stage: str
    trace: list[dict[str, Any]]


def _korean_char_count(text: str) -> int:
    return sum(1 for c in text if "\uAC00" <= c <= "\uD7A3")


def _has_economic_signal(text: str, *, korean_count: int) -> bool:
    if any(kw in text for kw in _KOREAN_ECONOMIC_KEYWORDS):
        return True
    if korean_count < 30:
        words = set(re.findall(r"\b[a-z]+\b", text))
        return bool(words & _ENGLISH_ECONOMIC_KEYWORDS_STRICT)
    return False  # 키워드 매칭 없으면 skip


def _has_direct_consumer_cost_signal(text: str, *, korean_count: int) -> bool:
    if any(kw in text for kw in _KOREAN_DIRECT_COST_KEYWORDS):
        return True
    if korean_count < 30:
        normalized_text = re.sub(r"\s+", " ", text)
        if any(kw in normalized_text for kw in _ENGLISH_DIRECT_COST_KEYWORDS):
            return True
        words = set(re.findall(r"\b[a-z]+\b", normalized_text))
        return bool(words & _ENGLISH_DIRECT_COST_KEYWORDS)
    return False


def _append_trace(state: NewsState, node: str, *, llm: bool, detail: str, elapsed: float | None = None) -> list[dict[str, Any]]:
    trace = list(state.get("trace") or [])
    item: dict[str, Any] = {"node": node, "llm": llm, "detail": detail}
    if elapsed is not None:
        item["elapsed"] = round(elapsed, 2)
    trace.append(item)
    return trace


def _extract_summary_field(summary: str, field_name: str) -> str:
    pattern = rf"(?im)^{re.escape(field_name)}:\s*(.+)$"
    match = re.search(pattern, summary or "")
    return match.group(1).strip() if match else ""


def _summary_has_minimum_format(summary: str) -> bool:
    required = ("event", "cost_signal", "facts", "consumer_link")
    return all(_extract_summary_field(summary, field) for field in required)


def _summary_has_grounding_issue(content: str, summary: str) -> bool:
    content_lower = (content or "").lower()
    summary_lower = (summary or "").lower()

    # 숫자 일치 체크 제거: LLM이 단위 변환($→p, gallon→litre 등)하면 오탐 발생
    # 키워드 기반 체크만 유지: 요약에 inflation/CPI 등이 등장했는데 기사에 전혀 없으면 hallucination
    if any(keyword in summary_lower for keyword in _SUMMARY_GROUNDING_KEYWORDS):
        if not any(keyword in content_lower for keyword in _SUMMARY_GROUNDING_KEYWORDS):
            return True

    return False


def _count_phrase_hits(text: str, phrases: frozenset[str]) -> int:
    normalized = re.sub(r"\s+", " ", (text or "").lower())
    return sum(1 for phrase in phrases if phrase in normalized)


def _cost_signal_is_core_topic(title: str, content: str, summary: str) -> bool:
    title_lower = (title or "").lower()
    lead_lower = (content or "")[:1200].lower()
    summary_lower = (summary or "").lower()

    title_cost_hits = _count_phrase_hits(title_lower, _ENGLISH_DIRECT_COST_KEYWORDS)
    lead_cost_hits = _count_phrase_hits(lead_lower, _ENGLISH_DIRECT_COST_KEYWORDS)
    title_market_hits = _count_phrase_hits(title_lower, _ENGLISH_MARKET_TOPIC_KEYWORDS)
    lead_market_hits = _count_phrase_hits(lead_lower, _ENGLISH_MARKET_TOPIC_KEYWORDS)
    summary_cost_hits = _count_phrase_hits(summary_lower, _ENGLISH_DIRECT_COST_KEYWORDS)

    if title_cost_hits > 0:
        return True
    if lead_cost_hits >= 1 and title_market_hits == 0 and lead_market_hits <= 1:
        return True
    if summary_cost_hits > 0 and lead_cost_hits > title_market_hits + lead_market_hits:
        return True
    return False


def _skip_from_summary(summary: str, event: str, reason: str) -> dict[str, Any]:
    return {
        "summary": summary,
        "result": {
            "summary": summary,
            "event": event,
            "mechanism": "",
            "related_indicators": [],
            "reliability": 0.0,
            "reliability_reason": reason,
            "effects": [],
            "_skip": True,
        },
    }


def pre_filter_node(state: NewsState) -> NewsState:
    news = state["news"]
    started_at = time.perf_counter()

    title_lower = (news.get("title") or "").lower()
    if any(pattern in title_lower for pattern in _LIVE_BLOG_TITLE_PATTERNS):
        elapsed = time.perf_counter() - started_at
        return {
            "result": {
                "summary": "",
                "event": "",
                "mechanism": "",
                "related_indicators": [],
                "reliability": 0.0,
                "reliability_reason": "Live blog / rolling news article filtered before LLM.",
                "effects": [],
                "_skip": True,
            },
            "stage": "pre_filter",
            "trace": _append_trace(
                state,
                "pre_filter",
                llm=False,
                elapsed=elapsed,
                detail=f"result=skip(live_blog) title={title_lower[:60]}",
            ),
        }

    text = (title_lower + " " + (news.get("content") or "").lower())
    korean_count = _korean_char_count(text)
    economic = _has_economic_signal(text, korean_count=korean_count)
    direct_cost = _has_direct_consumer_cost_signal(text, korean_count=korean_count)

    db_keywords = set(build_english_fallback_map().keys())
    news_keywords = {str(k).lower().strip() for k in (news.get("keyword") or [])}
    keyword_match = bool(news_keywords & db_keywords)
    elapsed = time.perf_counter() - started_at

    if not economic and not keyword_match:
        return {
            "result": {
                "summary": "",
                "event": "",
                "mechanism": "",
                "related_indicators": [],
                "reliability": 0.0,
                "reliability_reason": "No economic signal detected before LLM stage.",
                "effects": [],
                "_skip": True,
            },
            "stage": "pre_filter",
            "trace": _append_trace(
                state,
                "pre_filter",
                llm=False,
                elapsed=elapsed,
                detail=f"result=skip(non_economic) korean_chars={korean_count}",
            ),
        }

    if news.get("allowed_categories") and not direct_cost and not keyword_match:
        return {
            "result": {
                "summary": "",
                "event": "",
                "mechanism": "",
                "related_indicators": [],
                "reliability": 0.0,
                "reliability_reason": "No direct consumer-cost signal detected in scoped run.",
                "effects": [],
                "_skip": True,
            },
            "stage": "pre_filter",
            "trace": _append_trace(
                state,
                "pre_filter",
                llm=False,
                elapsed=elapsed,
                detail=(
                    f"result=skip(no_direct_cost_signal) korean_chars={korean_count} "
                    f"economic={economic} keyword_match={keyword_match}"
                ),
            ),
        }

    return {
        "stage": "pre_filter",
        "trace": _append_trace(
            state,
            "pre_filter",
            llm=False,
            elapsed=elapsed,
            detail=(
                f"result=pass korean_chars={korean_count} economic={economic} "
                f"direct_cost={direct_cost} keyword_match={keyword_match}"
            ),
        ),
    }


def route_after_pre_filter(state: NewsState) -> str:
    return "skip" if state.get("result") else "continue"


async def summarize_node(state: NewsState) -> NewsState:
    news = state["news"]
    news_id = str(news.get("id") or "")
    title = news.get("title", "")
    content = news.get("content") or title
    if not content:
        raise ValueError("News content is empty.")
    started_at = time.perf_counter()
    summary = await run_summary_chain(content, news_id=news_id)
    grounding_issue = _summary_has_grounding_issue(content, summary)
    elapsed = time.perf_counter() - started_at
    print(f"[summarize][news_id={news_id}] elapsed={elapsed:.2f}s")
    consumer_link = _extract_summary_field(summary, "consumer_link").lower()
    cost_signal = _extract_summary_field(summary, "cost_signal").lower()
    event = _extract_summary_field(summary, "event")
    has_minimum_format = _summary_has_minimum_format(summary)

    if grounding_issue:
        return {
            **_skip_from_summary(
                summary,
                event,
                "LLM1 summary was not grounded in the source article.",
            ),
            "stage": "summarize",
            "trace": _append_trace(
                state,
                "summarize",
                llm=True,
                elapsed=elapsed,
                detail=(
                    f"input=raw_news.content result=skip "
                    f"format={'ok' if has_minimum_format else 'broken'} "
                    f"consumer_link={consumer_link or 'missing'} "
                    f"cost_signal={cost_signal or 'missing'} grounding=failed"
                ),
            ),
        }
    if not has_minimum_format:
        return {
            **_skip_from_summary(
                summary,
                event,
                "LLM1 returned a broken summary format.",
            ),
            "stage": "summarize",
            "trace": _append_trace(
                state,
                "summarize",
                llm=True,
                elapsed=elapsed,
                detail=(
                    f"input=raw_news.content result=skip "
                    f"format=broken "
                    f"consumer_link={consumer_link or 'missing'} cost_signal={cost_signal or 'missing'}"
                ),
            ),
        }
    if consumer_link != "yes":
        return {
            **_skip_from_summary(
                summary,
                event,
                "LLM1 judged the article unrelated to consumer cost impact.",
            ),
            "stage": "summarize",
            "trace": _append_trace(
                state,
                "summarize",
                llm=True,
                elapsed=elapsed,
                detail=(
                    f"input=raw_news.content result=skip "
                    f"format=ok consumer_link={consumer_link or 'missing'} "
                    f"cost_signal={cost_signal or 'missing'}"
                ),
            ),
        }
    if cost_signal not in {"up", "down"}:
        return {
            **_skip_from_summary(
                summary,
                event,
                "LLM1 did not provide a usable cost signal.",
            ),
            "stage": "summarize",
            "trace": _append_trace(
                state,
                "summarize",
                llm=True,
                elapsed=elapsed,
                detail=(
                    f"input=raw_news.content result=skip "
                    f"format=ok consumer_link={consumer_link} "
                    f"cost_signal={cost_signal or 'missing'}"
                ),
            ),
        }
    return {
        "summary": summary,
        "stage": "summarize",
        "trace": _append_trace(
            state,
            "summarize",
            llm=True,
            elapsed=elapsed,
            detail=(
                f"input=raw_news.content result=pass "
                f"format={'ok' if has_minimum_format else 'broken'} "
                f"consumer_link={consumer_link or 'missing'} cost_signal={cost_signal or 'missing'}"
            ),
        ),
    }


async def build_history_context_node(state: NewsState) -> NewsState:
    news = state["news"]
    news_id = str(news.get("id") or "")
    repo = news.get("_repo")
    started_at = time.perf_counter()
    if repo is not None:
        history_items = await asyncio.to_thread(
            repo.fetch_analysis_history,
            current_news_id=news["id"],
            keywords=news.get("keyword") or [],
            published_at=news.get("published_at"),
            limit=5,
        )
    else:
        history_items = news.get("history_items") or []

    history_context = build_history_context(history_items)
    elapsed = time.perf_counter() - started_at
    print(f"[history][news_id={news_id}] elapsed={elapsed:.2f}s items={len(history_items)}")
    return {
        "history_context": history_context,
        "stage": "build_history_context",
        "trace": _append_trace(
            state,
            "build_history_context",
            llm=False,
            elapsed=elapsed,
            detail=f"db=news_analyses+causal_chains items={len(history_items)}",
        ),
    }


async def build_indicator_context_node(state: NewsState) -> NewsState:
    news = state["news"]
    news_id = str(news.get("id") or "")
    repo = news.get("_repo")
    published_at = news.get("published_at")
    started_at = time.perf_counter()
    indicator_loaded = False
    indicator_context = "데이터 없음"

    if repo is not None and published_at:
        reference_date = str(published_at)[:10]
        try:
            indicators = await asyncio.to_thread(repo.fetch_indicators_by_date, reference_date=reference_date)

            def _fmt_series(series: list, fmt: str = "{:.1f}") -> str:
                if not series:
                    return ""
                months = [s[0] for s in series]
                values = ", ".join(fmt.format(s[1]) for s in series)
                return f"{months[0]}~{months[-1]}: {values}"

            lines = [f"날짜: {indicators['reference_date']}"]
            if s := _fmt_series(indicators.get("krw_usd_rate") or []):
                lines.append(f"KRW/USD 환율 (원):\n  {s}")
            if s := _fmt_series(indicators.get("wti") or [], "${:.2f}"):
                lines.append(f"원유 수입가 ($/배럴):\n  {s}")
            if s := _fmt_series(indicators.get("cpi_total") or []):
                lines.append(f"한국 CPI:\n  {s}")
            if s := _fmt_series(indicators.get("gpr") or []):
                lines.append(f"지정학적 리스크(GPR):\n  {s}")
            if s := _fmt_series(indicators.get("fred_wti") or [], "${:.2f}"):
                lines.append(f"WTI 현물가 ($/배럴):\n  {s}")
            if s := _fmt_series(indicators.get("fred_cpi") or []):
                lines.append(f"미국 CPI:\n  {s}")
            if (v := indicators.get("natural_gas_7d")) is not None:
                lines.append(f"천연가스 현물가 7일평균 ($/MMBtu): ${v:.2f}")
            if (v := indicators.get("heating_oil_7d")) is not None:
                lines.append(f"난방유 현물가 7일평균 ($/갤런): ${v:.3f}")
            if (v := indicators.get("usd_index_7d")) is not None:
                lines.append(f"달러인덱스 7일평균: {v:.2f}")
            if (v := indicators.get("gpr_7d")) is not None:
                lines.append(f"지정학적리스크(GPR) 7일평균: {v:.1f}")
            if (v := indicators.get("oil_disruptions_7d")) is not None:
                lines.append(f"원유공급위협(GPR-Oil) 7일평균: {v:.1f}")
            indicator_context = "\n".join(lines)
            indicator_loaded = True
        except Exception:
            pass

    elapsed = time.perf_counter() - started_at
    indicator_status = "loaded" if indicator_loaded else "none"
    print(f"[indicator][news_id={news_id}] elapsed={elapsed:.2f}s loaded={indicator_status}")
    return {
        "indicator_context": indicator_context,
        "stage": "build_indicator_context",
        "trace": _append_trace(
            state,
            "build_indicator_context",
            llm=False,
            elapsed=elapsed,
            detail=f"indicators={indicator_status}",
        ),
    }


async def extract_causal_node(state: NewsState) -> NewsState:
    news = state["news"]
    news_id = str(news.get("id") or "")
    started_at = time.perf_counter()
    causal_raw = await run_causal_chain(
        state["summary"],
        state.get("history_context", "없음"),
        categories=news.get("allowed_categories"),
        indicator_context=state.get("indicator_context", "데이터 없음"),
        news_id=news_id,
    )
    elapsed = time.perf_counter() - started_at
    print(f"[extract_causal][news_id={news_id}] elapsed={elapsed:.2f}s")
    return {
        "causal_raw": causal_raw,
        "stage": "extract_causal",
        "trace": _append_trace(
            state,
            "extract_causal",
            llm=True,
            elapsed=elapsed,
            detail="input=summary+history_context+allowed_categories",
        ),
    }


def validate_causal_node(state: NewsState) -> NewsState:
    started_at = time.perf_counter()
    try:
        news = state["news"]
        news_id = str(news.get("id") or "")
        causal_dict = parse_causal_json(state["causal_raw"])
        causal = normalize_causal(
            causal_dict,
            categories=news.get("allowed_categories"),
            summary=state.get("summary", ""),
        )

        if not causal.get("effects"):
            elapsed = time.perf_counter() - started_at
            print(f"[validate][news_id={news_id}] elapsed={elapsed:.2f}s result=skip(empty_effects)")
            return {
                "result": {"summary": state["summary"], **causal, "_skip": True},
                "error": "",
                "stage": "validate_causal",
                "trace": _append_trace(
                    state,
                    "validate_causal",
                    llm=False,
                    elapsed=elapsed,
                    detail="result=skip(empty_effects)",
                ),
            }
        validate_causal_result(causal, summary=state.get("summary", ""))
        result = {"summary": state["summary"], **causal}
        elapsed = time.perf_counter() - started_at
        print(f"[validate][news_id={news_id}] elapsed={elapsed:.2f}s result=success")
        return {
            "causal": causal,
            "result": result,
            "error": "",
            "stage": "validate_causal",
            "trace": _append_trace(
                state,
                "validate_causal",
                llm=False,
                elapsed=elapsed,
                detail="result=success",
            ),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        news_id = str(state.get("news", {}).get("id") or "")
        print(f"[validate][news_id={news_id}] elapsed={elapsed:.2f}s result=error")
        print(f"[LLM2][news_id={news_id}] parse error: {exc}")
        print(f"[LLM2][news_id={news_id}] raw_preview={state.get('causal_raw', '')[:200]}")
        return {
            "error": str(exc),
            "stage": "validate_causal",
            "trace": _append_trace(
                state,
                "validate_causal",
                llm=False,
                elapsed=elapsed,
                detail=f"result=error error={exc}",
            ),
        }


def build_news_pipeline():
    graph = StateGraph(NewsState)
    graph.add_node("pre_filter", pre_filter_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("build_history_context", build_history_context_node)
    graph.add_node("build_indicator_context", build_indicator_context_node)
    graph.add_node("extract_causal", extract_causal_node)
    graph.add_node("validate_causal", validate_causal_node)

    graph.add_edge(START, "pre_filter")
    graph.add_conditional_edges(
        "pre_filter",
        route_after_pre_filter,
        {"skip": END, "continue": "summarize"},
    )
    graph.add_conditional_edges(
        "summarize",
        lambda s: "skip" if s.get("result") else "continue",
        {"skip": END, "continue": "build_history_context"},
    )
    graph.add_edge("build_history_context", "build_indicator_context")
    graph.add_edge("build_indicator_context", "extract_causal")
    graph.add_edge("extract_causal", "validate_causal")
    graph.add_edge("validate_causal", END)
    return graph.compile()


NEWS_PIPELINE = build_news_pipeline()


async def analyze_news(news: dict[str, Any]) -> dict[str, Any]:
    final_state = await NEWS_PIPELINE.ainvoke({"news": news, "attempts": 0, "trace": []})
    result = final_state.get("result")
    if not result:
        stage = final_state.get("stage") or "unknown"
        error = final_state.get("error") or "News analysis graph failed."
        attempts = final_state.get("attempts") or 0
        raise ValueError(f"stage={stage} attempts={attempts} error={error}")
    return {**result, "_trace": final_state.get("trace") or []}
