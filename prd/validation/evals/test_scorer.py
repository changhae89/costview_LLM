"""scorer.py 단위 테스트.

실행:
    cd costview_LLM
    pytest validation/evals/test_scorer.py -v
"""
from __future__ import annotations

import pytest

from validation.scorer import (
    compute_r,
    score_change_pct,
    score_chain,
    score_direction,
    score_magnitude,
)
from validation.evals.cases import (
    CHAIN_CASES,
    CHANGE_PCT_CASES,
    COMPUTE_R_CASES,
    DIRECTION_CASES,
    MAGNITUDE_CASES,
)


# ---------------------------------------------------------------------------
# compute_r
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", COMPUTE_R_CASES, ids=[c["desc"] for c in COMPUTE_R_CASES])
def test_compute_r(case):
    result = compute_r(case["v_m"], case["v_m1"])
    assert result == pytest.approx(case["expected"], abs=0.01)


# ---------------------------------------------------------------------------
# score_direction
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", DIRECTION_CASES, ids=[c["desc"] for c in DIRECTION_CASES])
def test_score_direction(case):
    result = score_direction(case["model"], case["r"])
    assert result == case["expected"]


# ---------------------------------------------------------------------------
# score_magnitude
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", MAGNITUDE_CASES, ids=[c["desc"] for c in MAGNITUDE_CASES])
def test_score_magnitude(case):
    result = score_magnitude(case["model"], case["r"])
    assert result == case["expected"]


# ---------------------------------------------------------------------------
# score_change_pct
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", CHANGE_PCT_CASES, ids=[c["desc"] for c in CHANGE_PCT_CASES])
def test_score_change_pct(case):
    result = score_change_pct(case["min"], case["max"], case["r"])
    assert result == case["expected"]


# ---------------------------------------------------------------------------
# score_chain  (end-to-end)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", CHAIN_CASES, ids=[c["desc"] for c in CHAIN_CASES])
def test_score_chain(case):
    cs = score_chain(case["chain"], case["v_m"], case["v_m1"])
    exp = case["expected"]

    assert cs.r            == pytest.approx(exp["r"],           abs=0.01)
    assert cs.direction    == exp["direction"]
    assert cs.magnitude    == exp["magnitude"]
    assert cs.change_pct   == exp["change_pct"]
    assert cs.chain_score  == pytest.approx(exp["chain_score"], abs=0.01)
