"""Orchestration: fetch → score → keyword check → report."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from .config import HORIZON_MONTHS, NEUTRAL_THRESHOLD_PCT
from .db import fetch_cohort, fetch_followup_keyword_counts, fetch_indicator_daily_monthly_avg, fetch_indicator_values
from .mapping import CATEGORY_KEYWORDS, _DAILY_TABLES, get_category_mapping
from .scorer import AnalysisScore, ChainScore, aggregate_analysis, score_chain


# ---------------------------------------------------------------------------
# Date key helpers
# ---------------------------------------------------------------------------

def _next_month_first(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _advance_months(d: date, n: int) -> date:
    for _ in range(n):
        d = _next_month_first(d)
    return d


def _month_keys(news_month_m: date, date_key_col: str, horizon: int) -> tuple[str, str]:
    """Return (key_m, key_m+horizon) in the format the indicator table expects."""
    m_horizon = _advance_months(news_month_m, horizon)
    if date_key_col == "reference_month":
        return news_month_m.strftime("%Y-%m"), m_horizon.strftime("%Y-%m")
    return news_month_m.strftime("%Y-%m-%d"), m_horizon.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def run_validation(
    connection,
    *,
    start: str,
    end: str | None = None,
    horizon: int = HORIZON_MONTHS,
) -> tuple[list[ChainScore], list[AnalysisScore], dict[str, float]]:
    """Run backtest. Returns (chain_scores, analysis_scores, keyword_stats).

    keyword_stats: {category: follow-up_news_hit_rate}
    """
    rows = fetch_cohort(connection, start=start, end=end)
    if not rows:
        return [], [], {}

    # --- Bulk-fetch indicator values ---
    needed: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        mapping = get_category_mapping(row["category"], row.get("geo_scope"))
        if not mapping:
            continue
        table, value_col, date_key_col = mapping
        key_m, key_horizon = _month_keys(row["news_month_m"], date_key_col, horizon)
        needed[(table, value_col, date_key_col)].update((key_m, key_horizon))

    cache: dict[tuple[str, str, str], dict[str, float]] = {}
    for key, months in needed.items():
        table, value_col, date_key_col = key
        if table in _DAILY_TABLES:
            cache[key] = fetch_indicator_daily_monthly_avg(
                connection,
                table=table,
                value_col=value_col,
                month_keys=list(months),
            )
        else:
            cache[key] = fetch_indicator_values(
                connection,
                table=table,
                value_col=value_col,
                date_key_col=date_key_col,
                month_keys=list(months),
            )

    # --- Score each chain ---
    chains_by_analysis: dict[str, list[ChainScore]] = defaultdict(list)
    skipped_by_analysis: dict[str, int] = defaultdict(int)
    all_chain_scores: list[ChainScore] = []
    category_months: dict[str, set[date]] = defaultdict(set)

    for row in rows:
        na_id = str(row["news_analysis_id"])
        mapping = get_category_mapping(row["category"], row.get("geo_scope"))
        if not mapping:
            skipped_by_analysis[na_id] += 1
            continue

        # time_horizon 필터: long/medium 예측은 M+1 채점 제외
        time_horizon = row.get("time_horizon") or "short"
        if time_horizon == "long" and horizon == 1:
            skipped_by_analysis[na_id] += 1
            continue
        if time_horizon == "medium" and horizon == 1:
            skipped_by_analysis[na_id] += 1
            continue

        # reliability 필터: 0.6 미만 체인 제외
        reliability = float(row.get("reliability") or 0.0)
        if reliability < 0.6:
            skipped_by_analysis[na_id] += 1
            continue


        table, value_col, date_key_col = mapping
        key_m, key_horizon = _month_keys(row["news_month_m"], date_key_col, horizon)
        indicator = cache.get((table, value_col, date_key_col), {})
        v_m, v_horizon = indicator.get(key_m), indicator.get(key_horizon)

        if v_m is None or v_horizon is None:
            skipped_by_analysis[na_id] += 1
            continue

        cs = score_chain(row, v_m, v_horizon)
        chains_by_analysis[na_id].append(cs)
        all_chain_scores.append(cs)

        if row["category"] in CATEGORY_KEYWORDS:
            category_months[row["category"]].add(row["news_month_m"])

    # --- Aggregate per analysis (method B) ---
    all_na_ids = {str(row["news_analysis_id"]) for row in rows}
    analysis_scores = [
        aggregate_analysis(na_id, chains_by_analysis[na_id], skipped_by_analysis[na_id])
        for na_id in sorted(all_na_ids)
    ]

    keyword_stats = _keyword_check(connection, category_months, horizon)

    return all_chain_scores, analysis_scores, keyword_stats


def _keyword_check(
    connection,
    category_months: dict[str, set[date]],
    horizon: int = HORIZON_MONTHS,
) -> dict[str, float]:
    """카테고리별로 M+HORIZON 기간에 관련 뉴스가 등장했는지 비율 반환."""
    if not category_months:
        return {}

    all_months = {m for months in category_months.values() for m in months}
    followup_start = _advance_months(min(all_months), HORIZON_MONTHS).strftime("%Y-%m-%d")
    followup_end   = _advance_months(_next_month_first(max(all_months)), HORIZON_MONTHS).strftime("%Y-%m-%d")

    results: dict[str, float] = {}
    for category, months in category_months.items():
        keywords = CATEGORY_KEYWORDS.get(category, [])
        if not keywords:
            continue
        counts = fetch_followup_keyword_counts(
            connection,
            keywords=keywords,
            start_date=followup_start,
            end_date=followup_end,
        )
        hit = sum(
            1 for m in months
            if counts.get(_advance_months(m, HORIZON_MONTHS).strftime("%Y-%m-%d"), 0) > 0
        )
        results[category] = hit / len(months)

    return results


# ---------------------------------------------------------------------------
# Clustered validation (동월 × 카테고리 신호 집계)
# ---------------------------------------------------------------------------

def run_clustered_validation(
    connection,
    *,
    start: str,
    end: str | None = None,
    horizon: int = HORIZON_MONTHS,
) -> list[dict]:
    """동월 × 카테고리 단위로 LLM 신호를 다수결 집계해 지표와 비교."""
    from collections import Counter
    from .scorer import compute_r

    rows = fetch_cohort(connection, start=start, end=end)
    if not rows:
        return []

    needed: dict[tuple, set] = defaultdict(set)
    for row in rows:
        mapping = get_category_mapping(row["category"], row.get("geo_scope"))
        if not mapping:
            continue
        table, value_col, date_key_col = mapping
        key_m, key_h = _month_keys(row["news_month_m"], date_key_col, horizon)
        needed[(table, value_col, date_key_col)].update([key_m, key_h])

    cache: dict[tuple, dict] = {}
    for key, months in needed.items():
        table, value_col, date_key_col = key
        if table in _DAILY_TABLES:
            cache[key] = fetch_indicator_daily_monthly_avg(
                connection, table=table, value_col=value_col, month_keys=list(months)
            )
        else:
            cache[key] = fetch_indicator_values(
                connection, table=table, value_col=value_col,
                date_key_col=date_key_col, month_keys=list(months)
            )

    # (news_month_m, category, geo_scope) → direction 투표
    clusters: dict[tuple, Counter] = defaultdict(Counter)
    for row in rows:
        key = (row["news_month_m"], row["category"], row.get("geo_scope") or "global")
        clusters[key][row["direction"]] += 1

    results = []
    for (month, category, geo_scope), votes in sorted(clusters.items()):
        mapping = get_category_mapping(category, geo_scope)
        if not mapping:
            continue
        table, value_col, date_key_col = mapping
        key_m, key_h = _month_keys(month, date_key_col, horizon)
        indicator = cache.get((table, value_col, date_key_col), {})
        v_m, v_h = indicator.get(key_m), indicator.get(key_h)
        if v_m is None or v_h is None:
            continue

        r = compute_r(v_m, v_h)
        actual = "neutral" if abs(r) < NEUTRAL_THRESHOLD_PCT else ("up" if r > 0 else "down")

        up, down, neutral = votes.get("up", 0), votes.get("down", 0), votes.get("neutral", 0)

        # 다수결 — 동률이면 neutral 우선
        if up > down and up > neutral:
            agg = "up"
        elif down > up and down > neutral:
            agg = "down"
        else:
            agg = "neutral"

        results.append({
            "month": str(month),
            "category": category,
            "geo_scope": geo_scope,
            "signal_count": up + down + neutral,
            "up_votes": up, "down_votes": down, "neutral_votes": neutral,
            "aggregated_direction": agg,
            "actual_r": round(r, 4),
            "actual_direction": actual,
            "hit": agg == actual,
        })

    return results


def print_clustered_report(cluster_results: list[dict], horizon: int) -> None:
    if not cluster_results:
        return

    total = len(cluster_results)
    hits  = sum(1 for c in cluster_results if c["hit"])
    print(f"\n[클러스터 집계 방향 적중률 M+{horizon}]  클러스터={total}개  적중={hits}개 ({hits/total:.1%})")

    by_cat: dict[str, list] = defaultdict(list)
    for c in cluster_results:
        by_cat[c["category"]].append(c)

    print(f"  {'카테고리':<12} {'클러스터':>6}  {'적중률':>8}  {'평균신호수':>8}")
    print("  " + "-" * 42)
    for cat in sorted(by_cat):
        cats = by_cat[cat]
        cat_hits = sum(1 for c in cats if c["hit"])
        avg_sig  = sum(c["signal_count"] for c in cats) / len(cats)
        label    = _CATEGORY_KO.get(cat, cat)
        print(f"  {label:<12} {len(cats):>6}  {cat_hits/len(cats):>8.1%}  {avg_sig:>8.1f}")


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


def print_combined_report(
    results: list[tuple[list[ChainScore], list[AnalysisScore], dict[str, float], int]],
) -> None:
    """M+1/M+2/M+3 결과를 한 표로 출력."""
    if not results:
        return

    first_chains, first_analysis, _, _ = results[0]
    total = len(first_chains)
    if total == 0:
        print("채점 가능한 인과 체인이 없습니다.")
        return

    total_skipped = sum(a.skipped_chains for a in first_analysis)
    scored_count  = sum(1 for a in first_analysis if not math.isnan(a.analysis_score))
    horizons      = [r[3] for r in results]
    col_w         = 8

    def _pct(v: float) -> str:
        return f"{v:.1%}".rjust(col_w) if not math.isnan(v) else " " * (col_w - 3) + "N/A"

    def _score(v: float) -> str:
        return f"{v:.3f}".rjust(col_w) if not math.isnan(v) else " " * (col_w - 3) + "N/A"

    sep   = "  "
    h_row = sep.join(f"{'M+'+str(h):>{col_w}}" for h in horizons)
    bar   = "─" * (20 + (col_w + len(sep)) * len(horizons))

    total_news    = len(first_analysis)
    all_chains    = total + total_skipped

    print("=" * 64)
    print("뉴스 분석 검증 리포트")
    print("=" * 64)
    print(f"분석된 뉴스 수          : {total_news}건")
    print(f"LLM 생성 인과 체인 수   : {all_chains}개  (뉴스 1건당 카테고리별 복수 생성)")
    print(f"  └ 채점 가능           : {total}개  (지표 데이터 있음)")
    print(f"  └ 채점 제외           : {total_skipped}개  (지표 미적재 또는 카테고리 매핑 없음)")
    print(f"채점된 분석 건수        : {scored_count} / {total_news}건  (체인이 1개 이상 채점된 뉴스)")

    # ── 컴포넌트별 적중률 ──────────────────────────────────────
    print()
    print("[컴포넌트별 적중률]")
    print(f"{'':20}" + h_row)
    print(bar)

    metrics: list[tuple[float, ...]] = []
    for chain_scores, analysis_scores, _, _ in results:
        n       = len(chain_scores)
        dir_hit = sum(1 for c in chain_scores if c.direction  == 1.0) / n if n else float("nan")
        mag_hit = sum(1 for c in chain_scores if c.magnitude  == 1.0) / n if n else float("nan")
        pct_pool = [c for c in chain_scores if c.change_pct is not None]
        pct_hit  = sum(1 for c in pct_pool if c.change_pct == 1.0) / len(pct_pool) if pct_pool else float("nan")
        avg_chain = sum(c.chain_score for c in chain_scores) / n if n else float("nan")
        scored    = [a for a in analysis_scores if not math.isnan(a.analysis_score)]
        avg_anal  = sum(a.analysis_score for a in scored) / len(scored) if scored else float("nan")
        metrics.append((dir_hit, mag_hit, pct_hit, avg_chain, avg_anal))

    component_rows = [
        ("방향 적중률",       0, _pct),
        ("강도 적중률",       1, _pct),
        ("변화율 범위 적중률", 2, _pct),
        ("체인 평균 점수",    3, _score),
        ("분석 평균 점수",    4, _score),
    ]
    for label, idx, fmt in component_rows:
        vals = sep.join(fmt(m[idx]) for m in metrics)
        print(f"{label:<20}{vals}")

    # ── 카테고리별 방향 적중률 ────────────────────────────────
    print()
    print("[카테고리별 방향 적중률]")
    print(f"{'카테고리':<14}{'건수':>5}  " + h_row)
    print(bar)

    all_cats: set[str] = set()
    by_cat_all: list[dict[str, list[ChainScore]]] = []
    for chain_scores, _, _, _ in results:
        by_cat: dict[str, list[ChainScore]] = defaultdict(list)
        for c in chain_scores:
            by_cat[c.category].append(c)
            all_cats.add(c.category)
        by_cat_all.append(by_cat)

    for cat in sorted(all_cats):
        label = _CATEGORY_KO.get(cat, cat)
        count = len(by_cat_all[0].get(cat, []))
        vals  = []
        for by_cat in by_cat_all:
            cats = by_cat.get(cat, [])
            vals.append(_pct(sum(1 for c in cats if c.direction == 1.0) / len(cats)) if cats else f"{'—':>{col_w}}")
        print(f"{label:<14}{count:>5}  " + sep.join(vals))

    # ── 후속 뉴스 키워드 등장률 ───────────────────────────────
    all_kw_cats: set[str] = set()
    for _, _, kw, _ in results:
        all_kw_cats.update(kw.keys())

    if all_kw_cats:
        print()
        print("[후속 뉴스 키워드 등장률]")
        print(f"{'카테고리':<14}  " + h_row)
        print(bar)
        for cat in sorted(all_kw_cats):
            label = _CATEGORY_KO.get(cat, cat)
            vals  = [_pct(kw[cat]) if cat in kw else f"{'—':>{col_w}}" for _, _, kw, _ in results]
            print(f"{label:<14}  " + sep.join(vals))


def print_report(
    chain_scores: list[ChainScore],
    analysis_scores: list[AnalysisScore],
    keyword_stats: dict[str, float] | None = None,
    horizon: int = HORIZON_MONTHS,
) -> None:
    total = len(chain_scores)
    if total == 0:
        print("채점 가능한 인과 체인이 없습니다.")
        return

    dir_hit   = sum(1 for c in chain_scores if c.direction == 1.0) / total
    mag_hit   = sum(1 for c in chain_scores if c.magnitude == 1.0) / total
    pct_pool  = [c for c in chain_scores if c.change_pct is not None]
    pct_hit   = (
        sum(1 for c in pct_pool if c.change_pct == 1.0) / len(pct_pool)
        if pct_pool else float("nan")
    )
    avg_chain = sum(c.chain_score for c in chain_scores) / total

    scored_a      = [a for a in analysis_scores if not math.isnan(a.analysis_score)]
    avg_anal      = sum(a.analysis_score for a in scored_a) / len(scored_a) if scored_a else float("nan")
    total_skipped = sum(a.skipped_chains for a in analysis_scores)

    print("=" * 52)
    print(f"뉴스 분석 검증 리포트  (시차 M+{horizon})")
    print("=" * 52)
    print(f"채점된 인과 체인 수     : {total}개")
    print(f"채점 제외 체인 수       : {total_skipped}개  (지표 없음 또는 M+{horizon} 데이터 미수집)")
    print(f"채점된 분석 건수        : {len(scored_a)} / {len(analysis_scores)}건")

    # --- 복합 영향 지표 ---
    multi_analyses = [a for a in scored_a if a.eligible_chains >= 2]
    multi_all_hit  = [
        a for a in multi_analyses
        if a.analysis_score >= (1.0 - NEUTRAL_THRESHOLD_PCT / 100)
    ]
    print(f"다중 카테고리 분석      : {len(multi_analyses)}건  (2개 이상 체인 채점)")
    if multi_analyses:
        print(f"  └ 전체 적중 (≥0.99)  : {len(multi_all_hit)}건  ({len(multi_all_hit)/len(multi_analyses):.1%})")

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

    # --- 카테고리별 방향 적중률 ---
    by_cat: dict[str, list[ChainScore]] = defaultdict(list)
    for c in chain_scores:
        by_cat[c.category].append(c)

    print()
    print("[카테고리별 방향 적중률]")
    for cat in sorted(by_cat):
        cats  = by_cat[cat]
        hit   = sum(1 for c in cats if c.direction == 1.0) / len(cats)
        label = _CATEGORY_KO.get(cat, cat)
        print(f"  {label:<12} {hit:.1%}  ({len(cats)}건)")

    # --- 후속 뉴스 키워드 등장률 ---
    if keyword_stats:
        print()
        print(f"[M+{horizon} 후속 뉴스 키워드 등장률]")
        print(f"  (예측한 카테고리 관련 뉴스가 M+{horizon}에 실제로 보도됐는가)")
        for cat in sorted(keyword_stats):
            label = _CATEGORY_KO.get(cat, cat)
            rate  = keyword_stats[cat]
            print(f"  {label:<12} {rate:.1%}")
