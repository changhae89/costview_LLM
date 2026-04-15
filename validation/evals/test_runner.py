"""runner.py 통합 테스트 (DB mock).

실행:
    cd costview_LLM
    pytest validation/evals/test_runner.py -v
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from validation.runner import run_validation
from validation.scorer import AnalysisScore, ChainScore


# ---------------------------------------------------------------------------
# DB mock 헬퍼
# ---------------------------------------------------------------------------

def _make_cohort_row(
    *,
    raw_news_id="rn-1",
    news_analysis_id="na-1",
    causal_chain_id="cc-1",
    origin_published_at=None,
    news_month_m=date(2025, 1, 1),
    category="oil",
    direction="up",
    magnitude="high",
    change_pct_min=None,
    change_pct_max=None,
) -> dict:
    return {
        "raw_news_id": raw_news_id,
        "news_analysis_id": news_analysis_id,
        "causal_chain_id": causal_chain_id,
        "origin_published_at": origin_published_at,
        "news_month_m": news_month_m,
        "category": category,
        "direction": direction,
        "magnitude": magnitude,
        "change_pct_min": change_pct_min,
        "change_pct_max": change_pct_max,
    }


# ---------------------------------------------------------------------------
# 테스트
# ---------------------------------------------------------------------------

@patch("validation.runner.fetch_indicator_values")
@patch("validation.runner.fetch_cohort")
def test_run_validation_single_chain_full_hit(mock_cohort, mock_indicator):
    """oil 카테고리 단일 체인, 방향·강도 모두 적중."""
    mock_cohort.return_value = [
        _make_cohort_row(
            category="oil", direction="up", magnitude="high",
            news_month_m=date(2025, 1, 1),
        )
    ]
    # M=2025-01-01, M+1=2025-02-01 / oil → ecos_monthly import_price_crude_oil
    mock_indicator.return_value = {
        "2025-01-01": 212.88,
        "2025-02-01": 235.96,   # R ≈ +10.84% → up, high
    }

    conn = MagicMock()
    chain_scores, analysis_scores = run_validation(conn, start="2025-01-01")

    assert len(chain_scores) == 1
    cs: ChainScore = chain_scores[0]
    assert cs.direction   == 1.0
    assert cs.magnitude   == 1.0
    assert cs.change_pct  is None
    assert cs.chain_score == pytest.approx(1.0, abs=0.01)

    assert len(analysis_scores) == 1
    assert analysis_scores[0].analysis_score == pytest.approx(1.0, abs=0.01)
    assert analysis_scores[0].eligible_chains == 1
    assert analysis_scores[0].skipped_chains  == 0


@patch("validation.runner.fetch_indicator_values")
@patch("validation.runner.fetch_cohort")
def test_run_validation_skips_unmapped_category(mock_cohort, mock_indicator):
    """매핑 없는 카테고리(shipping)는 skip 처리된다."""
    mock_cohort.return_value = [
        _make_cohort_row(category="shipping", direction="up", magnitude="low"),
    ]
    mock_indicator.return_value = {}

    conn = MagicMock()
    chain_scores, analysis_scores = run_validation(conn, start="2025-01-01")

    assert chain_scores == []
    assert analysis_scores[0].eligible_chains == 0
    assert analysis_scores[0].skipped_chains  == 1


@patch("validation.runner.fetch_indicator_values")
@patch("validation.runner.fetch_cohort")
def test_run_validation_skips_missing_m1(mock_cohort, mock_indicator):
    """M+1 지표 없으면 skip 처리된다."""
    mock_cohort.return_value = [
        _make_cohort_row(category="oil", direction="up", magnitude="high"),
    ]
    mock_indicator.return_value = {"2025-01-01": 212.88}  # M+1 없음

    conn = MagicMock()
    chain_scores, analysis_scores = run_validation(conn, start="2025-01-01")

    assert chain_scores == []
    assert analysis_scores[0].skipped_chains == 1


@patch("validation.runner.fetch_indicator_values")
@patch("validation.runner.fetch_cohort")
def test_run_validation_method_b_aggregation(mock_cohort, mock_indicator):
    """같은 news_analysis_id 아래 체인 2개 → method B (평균) 적용."""
    mock_cohort.return_value = [
        _make_cohort_row(
            news_analysis_id="na-1", causal_chain_id="cc-1",
            category="oil", direction="up", magnitude="high",
        ),
        _make_cohort_row(
            news_analysis_id="na-1", causal_chain_id="cc-2",
            category="inflation", direction="down", magnitude="low",
        ),
    ]

    def _indicator_side_effect(connection, *, table, value_col, date_key_col, month_keys):
        if value_col == "import_price_crude_oil":
            return {"2025-01-01": 212.88, "2025-02-01": 235.96}  # R≈+10.84% → up,high → 1.0
        if value_col == "fred_cpi":
            return {"2025-01": 326.588, "2025-02": 327.46}        # R≈+0.27% → neutral,low
        return {}

    mock_indicator.side_effect = _indicator_side_effect

    conn = MagicMock()
    chain_scores, analysis_scores = run_validation(conn, start="2025-01-01")

    assert len(chain_scores) == 2
    oil_cs   = next(c for c in chain_scores if c.category == "oil")
    infl_cs  = next(c for c in chain_scores if c.category == "inflation")

    assert oil_cs.chain_score  == pytest.approx(1.0,  abs=0.01)   # 완전 적중
    assert infl_cs.chain_score == pytest.approx(0.5,  abs=0.01)   # 방향 미스, 강도 적중

    expected_analysis_score = (1.0 + 0.5) / 2
    assert analysis_scores[0].analysis_score == pytest.approx(expected_analysis_score, abs=0.01)


@patch("validation.runner.fetch_cohort")
def test_run_validation_empty_cohort(mock_cohort):
    """조회 결과 없으면 빈 리스트 반환."""
    mock_cohort.return_value = []
    conn = MagicMock()
    chain_scores, analysis_scores = run_validation(conn, start="2025-01-01")
    assert chain_scores    == []
    assert analysis_scores == []
