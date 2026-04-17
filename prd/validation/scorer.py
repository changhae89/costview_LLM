"""Scoring logic for validation backtest.

Scoring per chain:
  1. direction  — partial credit (1.0 hit / 0.5 pred≠neutral but actual=neutral / 0.0 opposite)
  2. magnitude  — partial credit (1.0 exact / 0.5 adjacent / 0.0 two apart)
  3. change_pct — binary (1.0 / 0.0), skipped (None) when both bounds are NULL

Chain score   = unweighted mean of applicable components.
Analysis score = unweighted mean of eligible chain scores (method B).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .config import (
    CHANGE_PCT_INCLUSIVE,
    MAGNITUDE_HIGH_MIN_PCT,
    MAGNITUDE_LOW_MAX_PCT,
    NEUTRAL_THRESHOLD_PCT,
)

_MAGNITUDE_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


# ---------------------------------------------------------------------------
# R
# ---------------------------------------------------------------------------

def compute_r(v_m: float, v_m1: float) -> float:
    """MoM % change: (v_m1 - v_m) / |v_m| * 100."""
    if v_m == 0:
        return 0.0
    return (v_m1 - v_m) / abs(v_m) * 100.0


# ---------------------------------------------------------------------------
# Component scores
# ---------------------------------------------------------------------------

def _realized_direction(r: float) -> str:
    if abs(r) < NEUTRAL_THRESHOLD_PCT:
        return "neutral"
    return "up" if r > 0 else "down"


def _realized_magnitude(r: float) -> str:
    a = abs(r)
    if a < MAGNITUDE_LOW_MAX_PCT:
        return "low"
    if a >= MAGNITUDE_HIGH_MIN_PCT:
        return "high"
    return "medium"


def score_direction(model_dir: str, r: float) -> float:
    realized = _realized_direction(r)
    if model_dir == realized:
        return 1.0
    # 실제가 neutral이면 방향이 완전히 반대는 아니므로 partial credit
    if realized == "neutral":
        return 0.5
    return 0.0


def score_magnitude(model_mag: str, r: float) -> float:
    diff = abs(
        _MAGNITUDE_ORDER.get(model_mag, 1) - _MAGNITUDE_ORDER.get(_realized_magnitude(r), 1)
    )
    return [1.0, 0.5, 0.0][min(diff, 2)]


def score_change_pct(
    pct_min: float | None,
    pct_max: float | None,
    r: float,
) -> float | None:
    """1.0 if R is within [min, max], 0.0 if not, None if both bounds NULL (skip)."""
    if pct_min is None and pct_max is None:
        return None
    lo = pct_min if pct_min is not None else float("-inf")
    hi = pct_max if pct_max is not None else float("inf")
    if CHANGE_PCT_INCLUSIVE:
        return 1.0 if lo <= r <= hi else 0.0
    return 1.0 if lo <= r < hi else 0.0


# ---------------------------------------------------------------------------
# Daily (any-day) scoring
# ---------------------------------------------------------------------------

def score_direction_any_day(model_dir: str, v_m: float, daily_values: list[float]) -> float:
    """1.0 if any day in M+N achieves the predicted direction vs M-month avg."""
    if not daily_values:
        return 0.0
    realized_days = [_realized_direction(compute_r(v_m, v)) for v in daily_values]
    if any(d == model_dir for d in realized_days):
        return 1.0
    if all(d == "neutral" for d in realized_days):
        return 0.5
    return 0.0


def score_magnitude_any_day(model_mag: str, v_m: float, daily_values: list[float]) -> float:
    """Magnitude scored against the peak |R| day."""
    if not daily_values:
        return 0.0
    max_abs_r = max(abs(compute_r(v_m, v)) for v in daily_values)
    diff = abs(
        _MAGNITUDE_ORDER.get(model_mag, 1) - _MAGNITUDE_ORDER.get(_realized_magnitude(max_abs_r), 1)
    )
    return [1.0, 0.5, 0.0][min(diff, 2)]


def score_change_pct_any_day(
    pct_min: float | None,
    pct_max: float | None,
    v_m: float,
    daily_values: list[float],
) -> float | None:
    """1.0 if any day's R falls within [min, max], None if bounds are both NULL."""
    if pct_min is None and pct_max is None:
        return None
    if not daily_values:
        return 0.0
    lo = pct_min if pct_min is not None else float("-inf")
    hi = pct_max if pct_max is not None else float("inf")
    rs = [compute_r(v_m, v) for v in daily_values]
    if CHANGE_PCT_INCLUSIVE:
        return 1.0 if any(lo <= r <= hi for r in rs) else 0.0
    return 1.0 if any(lo <= r < hi for r in rs) else 0.0


def score_chain_daily(row: dict, v_m: float, daily_values: list[float]) -> "ChainScore":
    """Score a chain using daily values: hit if any single day achieves the prediction."""
    dir_s = score_direction_any_day(row["direction"], v_m, daily_values)
    mag_s = score_magnitude_any_day(row["magnitude"], v_m, daily_values)
    pct_s = score_change_pct_any_day(row.get("change_pct_min"), row.get("change_pct_max"), v_m, daily_values)

    if pct_s is not None:
        chain_score = dir_s * 0.5 + mag_s * 0.3 + pct_s * 0.2
    else:
        chain_score = dir_s * (0.5 / 0.8) + mag_s * (0.3 / 0.8)

    # representative R: peak absolute day
    r = max((compute_r(v_m, v) for v in daily_values), key=abs)

    return ChainScore(
        causal_chain_id=str(row["causal_chain_id"]),
        news_analysis_id=str(row["news_analysis_id"]),
        category=row["category"],
        r=round(r, 4),
        direction=dir_s,
        magnitude=mag_s,
        change_pct=pct_s,
        chain_score=chain_score,
    )


# ---------------------------------------------------------------------------
# Chain-level score
# ---------------------------------------------------------------------------

@dataclass
class ChainScore:
    causal_chain_id: str
    news_analysis_id: str
    category: str
    r: float
    direction: float
    magnitude: float
    change_pct: float | None   # None = skipped
    chain_score: float


def score_chain(row: dict, v_m: float, v_m1: float) -> ChainScore:
    r = compute_r(v_m, v_m1)
    dir_s = score_direction(row["direction"], r)
    mag_s = score_magnitude(row["magnitude"], r)
    pct_s = score_change_pct(row.get("change_pct_min"), row.get("change_pct_max"), r)

    # 가중치: direction 50%, magnitude 30%, change_pct 20%
    if pct_s is not None:
        chain_score = dir_s * 0.5 + mag_s * 0.3 + pct_s * 0.2
    else:
        chain_score = dir_s * (0.5 / 0.8) + mag_s * (0.3 / 0.8)

    return ChainScore(
        causal_chain_id=str(row["causal_chain_id"]),
        news_analysis_id=str(row["news_analysis_id"]),
        category=row["category"],
        r=round(r, 4),
        direction=dir_s,
        magnitude=mag_s,
        change_pct=pct_s,
        chain_score=chain_score,
    )


# ---------------------------------------------------------------------------
# Analysis-level aggregation (method B)
# ---------------------------------------------------------------------------

@dataclass
class AnalysisScore:
    news_analysis_id: str
    eligible_chains: int
    skipped_chains: int
    analysis_score: float   # nan when no eligible chains


def aggregate_analysis(
    news_analysis_id: str,
    chain_scores: list[ChainScore],
    skipped: int,
) -> AnalysisScore:
    if not chain_scores:
        return AnalysisScore(
            news_analysis_id=news_analysis_id,
            eligible_chains=0,
            skipped_chains=skipped,
            analysis_score=float("nan"),
        )
    return AnalysisScore(
        news_analysis_id=news_analysis_id,
        eligible_chains=len(chain_scores),
        skipped_chains=skipped,
        analysis_score=sum(c.chain_score for c in chain_scores) / len(chain_scores),
    )
