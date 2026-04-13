from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from prd.db.fetch import fetch_analysis_history
from prd.db.supabase_store import fetch_analysis_history_sb
from prd.llm.chains.news_analysis_chain import (
    build_history_context,
    normalize_causal,
    parse_causal_json,
    run_causal_chain,
    run_repair_chain,
    run_summary_chain,
    validate_causal_result,
)

MAX_REPAIR_ATTEMPTS = 2


class NewsState(TypedDict, total=False):
    news: dict[str, Any]
    summary: str
    history_context: str
    causal_raw: str
    causal: dict[str, Any]
    result: dict[str, Any]
    attempts: int
    error: str
    stage: str
    trace: list[dict[str, Any]]


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
    if news.get("_history_backend") == "supabase":
        history_items = fetch_analysis_history_sb(
            news["_sb"],
            current_news_id=news["id"],
            keywords=news.get("keyword") or [],
            published_at=news.get("published_at"),
            limit=5,
        )
    elif news.get("_history_backend") == "postgres":
        history_items = fetch_analysis_history(
            news["_conn"],
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


async def extract_causal_node(state: NewsState) -> NewsState:
    news = state["news"]
    causal_raw = await run_causal_chain(
        state["summary"],
        state.get("history_context", "없음"),
        categories=news.get("allowed_categories"),
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
        attempts = int(state.get("attempts", 0)) + 1
        return {
            "attempts": attempts,
            "error": str(exc),
            "stage": "validate_causal",
            "trace": _append_trace(
                state,
                "validate_causal",
                llm=False,
                detail=f"result=parse_fail attempt={attempts}",
            ),
        }


async def repair_json_node(state: NewsState) -> NewsState:
    repaired = await run_repair_chain(state["summary"], state["causal_raw"])
    return {
        "causal_raw": repaired,
        "stage": "repair_json",
        "trace": _append_trace(
            state,
            "repair_json",
            llm=True,
            detail="input=summary+causal_raw",
        ),
    }


def fail_node(state: NewsState) -> NewsState:
    return {
        **state,
        "trace": _append_trace(
            state,
            "fail",
            llm=False,
            detail="result=max_repair_exceeded",
        ),
    }


def route_after_validate(state: NewsState) -> str:
    if state.get("result"):
        return "success"
    if int(state.get("attempts", 0)) <= MAX_REPAIR_ATTEMPTS:
        return "repair"
    return "fail"


def build_news_pipeline():
    graph = StateGraph(NewsState)
    graph.add_node("summarize", summarize_node)
    graph.add_node("build_history_context", build_history_context_node)
    graph.add_node("extract_causal", extract_causal_node)
    graph.add_node("validate_causal", validate_causal_node)
    graph.add_node("repair_json", repair_json_node)
    graph.add_node("fail", fail_node)

    graph.add_edge(START, "summarize")
    graph.add_edge("summarize", "build_history_context")
    graph.add_edge("build_history_context", "extract_causal")
    graph.add_edge("extract_causal", "validate_causal")
    graph.add_conditional_edges(
        "validate_causal",
        route_after_validate,
        {
            "success": END,
            "repair": "repair_json",
            "fail": "fail",
        },
    )
    graph.add_edge("repair_json", "validate_causal")
    graph.add_edge("fail", END)
    return graph.compile()


NEWS_PIPELINE = build_news_pipeline()


async def analyze_news(news: dict[str, Any]) -> dict[str, Any]:
    final_state = await NEWS_PIPELINE.ainvoke({"news": news, "attempts": 0, "trace": []})
    result = final_state.get("result")
    if not result:
        stage = final_state.get("stage") or "unknown"
        attempts = int(final_state.get("attempts", 0))
        error = final_state.get("error") or "News analysis graph failed."
        raise ValueError(f"stage={stage} attempts={attempts} error={error}")
    return {**result, "_trace": final_state.get("trace") or []}
