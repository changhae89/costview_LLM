from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from prd.llm.chains.causal_normalizer import (
    normalize_causal,
    parse_causal_json,
    validate_causal_result,
)
from prd.llm.chains.category_registry import CATEGORY_FALLBACK_MAP, build_english_fallback_map
from prd.llm.chains.history_builder import build_history_context
from prd.llm.chains.llm_runner import run_causal_chain, run_repair_chain, run_summary_chain

MAX_REPAIR_ATTEMPTS = 3

_KOREAN_ECONOMIC_KEYWORDS: frozenset[str] = frozenset(CATEGORY_FALLBACK_MAP.keys())

# 영어 본문 텍스트 매칭용: generic 단어(oil, gas, food, cost, price) 제외하고 구체적 용어만 사용
_ENGLISH_ECONOMIC_KEYWORDS_STRICT: frozenset[str] = frozenset({
    "crude", "petroleum", "opec", "barrel", "wti", "brent",  # oil
    "gasoline", "petrol", "diesel",                           # fuel
    "lng", "lpg",                                             # gas
    "electricity", "utility",                                 # energy
    "grocery", "dairy", "soybean",                            # food
    "wheat", "grain", "corn",                                 # wheat
    "freight", "logistics",                                   # shipping
    "inflation", "deflation", "stagflation", "cpi",           # price/inflation
})


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


def _append_trace(state: NewsState, node: str, *, llm: bool, detail: str) -> list[dict[str, Any]]:
    trace = list(state.get("trace") or [])
    trace.append(
        {
            "node": node,
            "llm": llm,
            "detail": detail,
        }
    )
    return trace


def pre_filter_node(state: NewsState) -> NewsState:
    news = state["news"]

    # When caller explicitly scopes categories, skip content-based pre-filter
    if news.get("allowed_categories"):
        return {
            "stage": "pre_filter",
            "trace": _append_trace(
                state,
                "pre_filter",
                llm=False,
                detail="result=pass(categories_provided)",
            ),
        }

    text = ((news.get("title") or "") + " " + (news.get("content") or "")).lower()
    korean_count = _korean_char_count(text)
    economic = _has_economic_signal(text, korean_count=korean_count)

    db_keywords = set(build_english_fallback_map().keys())
    news_keywords = {str(k).lower().strip() for k in (news.get("keyword") or [])}
    keyword_match = bool(news_keywords & db_keywords)

    if korean_count < 30 and not economic and not keyword_match:
        return {
            "result": {
                "summary": "",
                "event": "",
                "mechanism": "",
                "related_indicators": [],
                "reliability": 0.0,
                "effects": [],
                "_skip": True,
            },
            "stage": "pre_filter",
            "trace": _append_trace(
                state,
                "pre_filter",
                llm=False,
                detail=f"result=skip(non_economic) korean_chars={korean_count}",
            ),
        }

    return {
        "stage": "pre_filter",
        "trace": _append_trace(
            state,
            "pre_filter",
            llm=False,
            detail=f"result=pass korean_chars={korean_count} economic={economic} keyword_match={keyword_match}",
        ),
    }


def route_after_pre_filter(state: NewsState) -> str:
    return "skip" if state.get("result") else "continue"


async def summarize_node(state: NewsState) -> NewsState:
    news = state["news"]
    content = news.get("content") or news.get("title", "")
    if not content:
        raise ValueError("News content is empty.")
    summary = await run_summary_chain(content)
    return {
        "summary": summary,
        "stage": "summarize",
        "trace": _append_trace(
            state,
            "summarize",
            llm=True,
            detail="input=raw_news.content",
        ),
    }


def build_history_context_node(state: NewsState) -> NewsState:
    news = state["news"]
    repo = news.get("_repo")
    if repo is not None:
        history_items = repo.fetch_analysis_history(
            current_news_id=news["id"],
            keywords=news.get("keyword") or [],
            published_at=news.get("published_at"),
            limit=5,
        )
    else:
        history_items = news.get("history_items") or []

    history_context = build_history_context(history_items)
    return {
        "history_context": history_context,
        "stage": "build_history_context",
        "trace": _append_trace(
            state,
            "build_history_context",
            llm=False,
            detail="db=news_analyses+causal_chains",
        ),
    }


def build_indicator_context_node(state: NewsState) -> NewsState:
    news = state["news"]
    repo = news.get("_repo")
    published_at = news.get("published_at")
    indicator_context = "데이터 없음"

    if repo is not None and published_at:
        reference_date = str(published_at)[:10]
        try:
            indicators = repo.fetch_indicators_by_date(reference_date=reference_date)

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
            indicator_context = "\n".join(lines)
        except Exception:
            pass

    return {
        "indicator_context": indicator_context,
        "stage": "build_indicator_context",
        "trace": _append_trace(
            state,
            "build_indicator_context",
            llm=False,
            detail=f"indicators={'loaded' if indicator_context != '데이터 없음' else 'none'}",
        ),
    }


async def extract_causal_node(state: NewsState) -> NewsState:
    news = state["news"]
    causal_raw = await run_causal_chain(
        state["summary"],
        state.get("history_context", "없음"),
        categories=news.get("allowed_categories"),
        indicator_context=state.get("indicator_context", "데이터 없음"),
    )
    return {
        "causal_raw": causal_raw,
        "stage": "extract_causal",
        "trace": _append_trace(
            state,
            "extract_causal",
            llm=True,
            detail="input=summary+history_context+allowed_categories",
        ),
    }


def validate_causal_node(state: NewsState) -> NewsState:
    try:
        news = state["news"]
        causal_dict = parse_causal_json(state["causal_raw"])
        causal = normalize_causal(causal_dict, categories=news.get("allowed_categories"))
        if not causal.get("effects"):
            return {
                "result": {"summary": state["summary"], **causal, "_skip": True},
                "error": "",
                "stage": "validate_causal",
                "trace": _append_trace(
                    state,
                    "validate_causal",
                    llm=False,
                    detail="result=skip(empty_effects)",
                ),
            }
        validate_causal_result(causal)
        result = {"summary": state["summary"], **causal}
        return {
            "causal": causal,
            "result": result,
            "error": "",
            "stage": "validate_causal",
            "trace": _append_trace(
                state,
                "validate_causal",
                llm=False,
                detail="result=success",
            ),
        }
    except Exception as exc:
        print(f"[LLM2] parse error: {exc}")
        print(f"[LLM2] raw output: {state.get('causal_raw', '')[:500]}")
        return {
            "error": str(exc),
            "stage": "validate_causal",
            "trace": _append_trace(
                state,
                "validate_causal",
                llm=False,
                detail=f"result=error error={exc}",
            ),
        }


def route_after_validate_causal(state: NewsState) -> str:
    if state.get("result") is not None:
        return "done"
    attempts = state.get("attempts") or 0
    if attempts < MAX_REPAIR_ATTEMPTS:
        return "repair"
    return "done"


async def repair_causal_node(state: NewsState) -> NewsState:
    summary = state.get("summary", "")
    causal_raw = state.get("causal_raw", "")
    repaired = await run_repair_chain(summary, causal_raw)
    attempts = (state.get("attempts") or 0) + 1
    return {
        "causal_raw": repaired,
        "attempts": attempts,
        "stage": "repair_causal",
        "trace": _append_trace(
            state,
            "repair_causal",
            llm=True,
            detail=f"attempt={attempts}",
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
    graph.add_node("repair_causal", repair_causal_node)
    graph.add_edge("extract_causal", "validate_causal")
    graph.add_conditional_edges(
        "validate_causal",
        route_after_validate_causal,
        {"done": END, "repair": "repair_causal"},
    )
    graph.add_edge("repair_causal", "validate_causal")
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
