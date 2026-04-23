"""LLM3 briefing chain — generates a daily consumer price briefing."""

from __future__ import annotations

import json
from typing import Any

from prd.config import get_gemini_api_key, get_gemini_model
from prd.llm.chains.llm_runner import _create_model, _message_text, _preview_text
from prd.llm.prompts.briefing_prompt import BRIEFING_PROMPT


def _fmt_indicator(indicators: dict) -> str:
    lines: list[str] = []
    if v := indicators.get("krw_usd_rate"):
        lines.append(f"원/달러 환율: {v:,.0f}원")
    if v := indicators.get("fred_wti") or indicators.get("wti"):
        lines.append(f"국제 유가(WTI): ${v:.1f}/배럴")
    if v := indicators.get("cpi_total"):
        lines.append(f"한국 소비자물가(CPI): {v:.1f}%")
    if v := indicators.get("gpr_7d") or indicators.get("gpr"):
        lines.append(f"지정학적 리스크(GPR): {v:.0f}")
    return "\n".join(lines) if lines else "최신 지표 없음"


def _fmt_categories(causal_rows: list[dict]) -> str:
    agg: dict[str, dict[str, int]] = {}
    for row in causal_rows:
        cat = row.get("category") or "기타"
        cat_ko = row.get("category_ko") or cat
        direction = row.get("direction") or "neutral"
        if cat not in agg:
            agg[cat] = {"category_ko": cat_ko, "up": 0, "down": 0, "neutral": 0}
        agg[cat][direction] = agg[cat].get(direction, 0) + 1

    lines: list[str] = []
    for entry in sorted(agg.values(), key=lambda x: x["up"] + x["down"], reverse=True)[:8]:
        name = entry["category_ko"]
        lines.append(f"- {name}: 상승 {entry['up']}건 / 하락 {entry['down']}건 / 중립 {entry['neutral']}건")
    return "\n".join(lines) if lines else "집계 데이터 없음"


def _fmt_news(analyses: list[dict]) -> str:
    lines: list[str] = []
    for i, row in enumerate(analyses[:10], 1):
        summary = (row.get("summary") or "").strip()
        reliability = row.get("reliability") or 0
        if summary:
            lines.append(f"{i}. [{reliability:.0%}] {summary}")
    return "\n".join(lines) if lines else "분석 데이터 없음"


async def run_briefing_chain(
    *,
    briefing_date: str,
    analyses: list[dict],
    causal_rows: list[dict],
    indicators: dict,
) -> dict[str, Any]:
    indicator_summary = _fmt_indicator(indicators)
    category_summary = _fmt_categories(causal_rows)
    news_summary = _fmt_news(analyses)
    news_count = min(len(analyses), 10)

    payload = {
        "briefing_date": briefing_date,
        "indicator_summary": indicator_summary,
        "category_summary": category_summary,
        "news_summary": news_summary,
        "news_count": news_count,
    }

    model = _create_model(temperature=0.3, max_tokens=2048)
    chain = BRIEFING_PROMPT | model
    print(f"[LLM3] request date={briefing_date} news_count={news_count}")
    response = await chain.ainvoke(payload)
    text = _message_text(response)
    print(f"[LLM3] response_preview={_preview_text(text)}")

    raw = text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:])
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]

    result = json.loads(raw)
    result.setdefault("headline", "오늘의 물가 브리핑")
    result.setdefault("overview", "")
    result.setdefault("items", [])
    result.setdefault("overall_risk", "medium")
    result.setdefault("consumer_tip", None)
    return result
