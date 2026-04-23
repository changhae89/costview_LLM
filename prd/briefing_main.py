"""
일별 물가 브리핑 생성 엔트리포인트
====================================
오늘 분석된 news_analyses + causal_chains를 집계하여
Gemini LLM3로 일반 소비자용 브리핑을 생성하고
daily_briefings 테이블에 저장합니다.

실행:
  python -m prd.briefing_main
  python -m prd.briefing_main --date 2025-01-15
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prd.config import load_environment
from prd.db.supabase_client import create_sb
from prd.llm.chains.briefing_runner import run_briefing_chain


def _log(msg: str) -> None:
    print(f"[briefing] {msg}")


def _fetch_today_analyses(sb, briefing_date: str) -> list[dict]:
    date_from = (date.fromisoformat(briefing_date) - timedelta(days=1)).isoformat()
    rows = (
        sb.table("news_analyses")
        .select("id, summary, reliability, effect_chain, time_horizon, korea_relevance")
        .gte("created_at", date_from)
        .lte("created_at", briefing_date + "T23:59:59")
        .gte("reliability", 0.6)
        .order("reliability", desc=True)
        .limit(20)
        .execute()
    ).data or []
    return rows


def _fetch_today_causal(sb, briefing_date: str) -> list[dict]:
    date_from = (date.fromisoformat(briefing_date) - timedelta(days=1)).isoformat()
    rows = (
        sb.table("causal_chains")
        .select("category, direction, magnitude")
        .gte("created_at", date_from)
        .lte("created_at", briefing_date + "T23:59:59")
        .execute()
    ).data or []
    return rows


def _fetch_latest_indicators(sb) -> dict:
    try:
        ecos = (
            sb.table("indicator_ecos_daily_logs")
            .select("krw_usd_rate, reference_date")
            .order("reference_date", desc=True)
            .limit(1)
            .execute()
        ).data or []
        fred = (
            sb.table("indicator_fred_daily_logs")
            .select("fred_wti, reference_date")
            .order("reference_date", desc=True)
            .limit(1)
            .execute()
        ).data or []
        kosis = (
            sb.table("indicator_kosis_monthly_logs")
            .select("cpi_total, reference_date")
            .order("reference_date", desc=True)
            .limit(1)
            .execute()
        ).data or []
        gpr = (
            sb.table("indicator_gpr_monthly_logs")
            .select("gpr_original, reference_date")
            .order("reference_date", desc=True)
            .limit(1)
            .execute()
        ).data or []

        result: dict = {}
        if ecos:
            result["krw_usd_rate"] = ecos[0].get("krw_usd_rate")
        if fred:
            result["fred_wti"] = fred[0].get("fred_wti")
        if kosis:
            result["cpi_total"] = kosis[0].get("cpi_total")
        if gpr:
            result["gpr"] = gpr[0].get("gpr_original")
        return result
    except Exception as e:
        _log(f"indicator fetch error: {e}")
        return {}


def _save_briefing(sb, briefing_date: str, result: dict, source_count: int, indicators: dict) -> None:
    row = {
        "briefing_date": briefing_date,
        "headline": result.get("headline", ""),
        "overview": result.get("overview", ""),
        "items": result.get("items", []),
        "overall_risk": result.get("overall_risk", "medium"),
        "consumer_tip": result.get("consumer_tip"),
        "indicators": indicators,
        "source_count": source_count,
    }
    sb.table("daily_briefings").upsert(row, on_conflict="briefing_date").execute()


async def main(briefing_date: str | None = None) -> None:
    load_environment()
    today = briefing_date or date.today().isoformat()
    _log(f"start date={today}")

    sb = create_sb()

    analyses = _fetch_today_analyses(sb, today)
    causal_rows = _fetch_today_causal(sb, today)
    indicators = _fetch_latest_indicators(sb)

    _log(f"analyses={len(analyses)} causal={len(causal_rows)} indicators={list(indicators.keys())}")

    result = await run_briefing_chain(
        briefing_date=today,
        analyses=analyses,
        causal_rows=causal_rows,
        indicators=indicators,
    )

    _log(f"headline={result.get('headline')}")
    _log(f"overall_risk={result.get('overall_risk')} items={len(result.get('items', []))}")

    _save_briefing(sb, today, result, source_count=len(analyses), indicators=indicators)
    _log("saved to daily_briefings")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    target_date = None
    for arg in sys.argv[1:]:
        if arg.startswith("--date="):
            target_date = arg.split("=", 1)[1].strip()
        elif not arg.startswith("--"):
            target_date = arg.strip()
    asyncio.run(main(target_date))
