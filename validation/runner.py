"""Orchestration: fetch → score → report."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from .db import fetch_cohort, fetch_indicator_values
from .mapping import CATEGORY_MAP
from .scorer import AnalysisScore, ChainScore, aggregate_analysis, score_chain


# ---------------------------------------------------------------------------
# Date key helpers
# ---------------------------------------------------------------------------

def _next_month_first(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _month_keys(news_month_m: date, date_key_col: str) -> tuple[str, str]:
    """Return (key_m, key_m1) in the format the indicator table expects."""
    m1 = _next_month_first(news_month_m)
    if date_key_col == "reference_month":
        return news_month_m.strftime("%Y-%m"), m1.strftime("%Y-%m")
    return news_month_m.strftime("%Y-%m-%d"), m1.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_validation(
    connection,
    *,
    start: str,
    end: str | None = None,
) -> tuple[list[ChainScore], list[AnalysisScore]]:
    """Run backtest for the given date range. Returns (chain_scores, analysis_scores)."""
    rows = fetch_cohort(connection, start=start, end=end)
    if not rows:
        return [], []

    # --- Collect all (table, value_col, date_key_col) → month keys needed ---
    needed: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        mapping = CATEGORY_MAP.get(row["category"])
        if not mapping:
            continue
        table, value_col, date_key_col = mapping
        key_m, key_m1 = _month_keys(row["news_month_m"], date_key_col)
        needed[(table, value_col, date_key_col)].update((key_m, key_m1))

    # --- Bulk-fetch indicator values ---
    cache: dict[tuple[str, str, str], dict[str, float]] = {
        key: fetch_indicator_values(
            connection,
            table=key[0],
            value_col=key[1],
            date_key_col=key[2],
            month_keys=list(months),
        )
        for key, months in needed.items()
    }

    # --- Score each chain ---
    chains_by_analysis: dict[str, list[ChainScore]] = defaultdict(list)
    skipped_by_analysis: dict[str, int] = defaultdict(int)
    all_chain_scores: list[ChainScore] = []

    for row in rows:
        na_id = str(row["news_analysis_id"])
        mapping = CATEGORY_MAP.get(row["category"])
        if not mapping:
            skipped_by_analysis[na_id] += 1
            continue

        table, value_col, date_key_col = mapping
        key_m, key_m1 = _month_keys(row["news_month_m"], date_key_col)
        indicator = cache.get((table, value_col, date_key_col), {})
        v_m, v_m1 = indicator.get(key_m), indicator.get(key_m1)

        if v_m is None or v_m1 is None:
            skipped_by_analysis[na_id] += 1
            continue

        cs = score_chain(row, v_m, v_m1)
        chains_by_analysis[na_id].append(cs)
        all_chain_scores.append(cs)

    # --- Aggregate per analysis (method B) ---
    all_na_ids = {str(row["news_analysis_id"]) for row in rows}
    analysis_scores = [
        aggregate_analysis(na_id, chains_by_analysis[na_id], skipped_by_analysis[na_id])
        for na_id in sorted(all_na_ids)
    ]

    return all_chain_scores, analysis_scores


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_CATEGORY_KO: dict[str, str] = {
    "oil":       "기름값(원유)",
    "fuel":      "주유비",
    "gas":       "가스비",
    "energy":    "전기세",
    "food":      "장바구니",
    "wheat":     "쌀·밀가루",
    "commodity": "생활용품",
    "price":     "물가",
    "inflation": "물가상승",
    "cost":      "생활비",
    "shipping":  "택배·운송비",
}


def print_report(chain_scores: list[ChainScore], analysis_scores: list[AnalysisScore]) -> None:
    total = len(chain_scores)
    if total == 0:
        print("채점 가능한 인과 체인이 없습니다.")
        return

    dir_hit  = sum(1 for c in chain_scores if c.direction == 1.0) / total
    mag_hit  = sum(1 for c in chain_scores if c.magnitude == 1.0) / total
    pct_pool = [c for c in chain_scores if c.change_pct is not None]
    pct_hit  = (
        sum(1 for c in pct_pool if c.change_pct == 1.0) / len(pct_pool)
        if pct_pool else float("nan")
    )
    avg_chain = sum(c.chain_score for c in chain_scores) / total

    scored_a      = [a for a in analysis_scores if not math.isnan(a.analysis_score)]
    avg_anal      = sum(a.analysis_score for a in scored_a) / len(scored_a) if scored_a else float("nan")
    total_skipped = sum(a.skipped_chains for a in analysis_scores)

    print("=" * 52)
    print("뉴스 분석 검증 리포트")
    print("=" * 52)
    print(f"채점된 인과 체인 수     : {total}개")
    print(f"채점 제외 체인 수       : {total_skipped}개  (지표 없음 또는 M+1 데이터 미수집)")
    print(f"채점된 분석 건수        : {len(scored_a)} / {len(analysis_scores)}건")
    print()
    print("[컴포넌트별 적중률]")
    print(f"  방향 적중률           : {dir_hit:.1%}  (상승/하락/중립 예측 정확도)")
    print(f"  강도 적중률           : {mag_hit:.1%}  (low/medium/high 완전 일치)")
    if not math.isnan(pct_hit):
        print(f"  변화율 범위 적중률    : {pct_hit:.1%}  ({len(pct_pool)}개 체인에서 범위 설정됨)")
    else:
        print(f"  변화율 범위 적중률    : 해당 없음  (변화율 범위를 설정한 체인 없음)")
    print()
    print("[종합 점수]")
    print(f"  체인 평균 점수        : {avg_chain:.3f}  (0~1, 높을수록 예측 정확)")
    print(f"  분석 평균 점수        : {avg_anal:.3f}  (체인 점수의 분석별 평균)")

    # 카테고리별 방향 적중률
    by_cat: dict[str, list[ChainScore]] = defaultdict(list)
    for c in chain_scores:
        by_cat[c.category].append(c)

    print()
    print("[카테고리별 방향 적중률]")
    for cat in sorted(by_cat):
        cats = by_cat[cat]
        hit  = sum(1 for c in cats if c.direction == 1.0) / len(cats)
        label = _CATEGORY_KO.get(cat, cat)
        print(f"  {label:<12} {hit:.1%}  ({len(cats)}건)")
