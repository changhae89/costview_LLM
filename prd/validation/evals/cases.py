"""Golden test cases for validation scoring.

각 케이스는 순수 데이터만 담는다.
pytest.approx 등 테스트 프레임워크 의존성은 test_*.py 에서 처리한다.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# compute_r  {"v_m", "v_m1", "expected", "desc"}
# ---------------------------------------------------------------------------
COMPUTE_R_CASES: list[dict] = [
    {"v_m": 100.0,  "v_m1": 103.0,  "expected":  3.0,    "desc": "상승 3%"},
    {"v_m": 100.0,  "v_m1":  97.0,  "expected": -3.0,    "desc": "하락 3%"},
    {"v_m": 100.0,  "v_m1": 100.5,  "expected":  0.5,    "desc": "소폭 상승 (중립 수준)"},
    {"v_m": 200.0,  "v_m1": 214.0,  "expected":  7.0,    "desc": "high 경계 정확히"},
    {"v_m":   0.0,  "v_m1":  10.0,  "expected":  0.0,    "desc": "분모 0 → 0 반환"},
    # 실제 DB 샘플: kosis cpi_total 2026-01→02
    {"v_m": 118.03, "v_m1": 118.4,  "expected":  0.3135, "desc": "실제 cpi_total 샘플"},
]

# ---------------------------------------------------------------------------
# score_direction  {"model", "r", "expected", "desc"}
# neutral threshold = 1.0%
# ---------------------------------------------------------------------------
DIRECTION_CASES: list[dict] = [
    # 일치
    {"model": "up",      "r":  3.0,  "expected": 1.0, "desc": "상승 예측, 실제 상승"},
    {"model": "down",    "r": -3.0,  "expected": 1.0, "desc": "하락 예측, 실제 하락"},
    {"model": "neutral", "r":  0.5,  "expected": 1.0, "desc": "중립 예측, 실제 중립"},
    # 불일치
    {"model": "up",      "r": -3.0,  "expected": 0.0, "desc": "상승 예측, 실제 하락"},
    {"model": "down",    "r":  3.0,  "expected": 0.0, "desc": "하락 예측, 실제 상승"},
    {"model": "neutral", "r":  3.0,  "expected": 0.0, "desc": "중립 예측, 실제 상승"},
    # 경계값 (neutral threshold = 1%)
    {"model": "up",      "r":  1.0,  "expected": 1.0, "desc": "R=1.0% → up (경계 초과)"},
    {"model": "neutral", "r":  1.0,  "expected": 0.0, "desc": "중립 예측, R=1.0% → 실제 up"},
    {"model": "up",      "r":  0.99, "expected": 0.5, "desc": "상승 예측, R=0.99% → 실제 neutral (partial)"},
]

# ---------------------------------------------------------------------------
# score_magnitude  {"model", "r", "expected", "desc"}
# low < 2% / 2% <= medium < 7% / high >= 7%
# exact=1.0 / adjacent=0.5 / two_apart=0.0
# ---------------------------------------------------------------------------
MAGNITUDE_CASES: list[dict] = [
    # 완전 일치
    {"model": "low",    "r":  1.0,  "expected": 1.0, "desc": "low 예측, 실제 low"},
    {"model": "medium", "r":  4.0,  "expected": 1.0, "desc": "medium 예측, 실제 medium"},
    {"model": "high",   "r":  8.0,  "expected": 1.0, "desc": "high 예측, 실제 high"},
    # 인접 (0.5점)
    {"model": "low",    "r":  4.0,  "expected": 0.5, "desc": "low 예측, 실제 medium"},
    {"model": "medium", "r":  1.0,  "expected": 0.5, "desc": "medium 예측, 실제 low"},
    {"model": "medium", "r":  8.0,  "expected": 0.5, "desc": "medium 예측, 실제 high"},
    {"model": "high",   "r":  4.0,  "expected": 0.5, "desc": "high 예측, 실제 medium"},
    # 2단계 차이 (0점)
    {"model": "low",    "r":  8.0,  "expected": 0.0, "desc": "low 예측, 실제 high"},
    {"model": "high",   "r":  1.0,  "expected": 0.0, "desc": "high 예측, 실제 low"},
    # 경계값
    {"model": "medium", "r":  2.0,  "expected": 1.0, "desc": "R=2.0% → medium (low/medium 경계)"},
    {"model": "high",   "r":  7.0,  "expected": 1.0, "desc": "R=7.0% → high (medium/high 경계)"},
]

# ---------------------------------------------------------------------------
# score_change_pct  {"min", "max", "r", "expected", "desc"}
# expected=None 은 skip (양쪽 NULL)
# ---------------------------------------------------------------------------
CHANGE_PCT_CASES: list[dict] = [
    {"min": 1.0,  "max": 5.0,  "r":  3.0,  "expected": 1.0,  "desc": "범위 내"},
    {"min": 1.0,  "max": 5.0,  "r":  6.0,  "expected": 0.0,  "desc": "범위 초과"},
    {"min": 1.0,  "max": 5.0,  "r":  1.0,  "expected": 1.0,  "desc": "하한 경계 (inclusive)"},
    {"min": 1.0,  "max": 5.0,  "r":  5.0,  "expected": 1.0,  "desc": "상한 경계 (inclusive)"},
    {"min": 1.0,  "max": 5.0,  "r":  0.9,  "expected": 0.0,  "desc": "하한 미만"},
    {"min": None, "max": 5.0,  "r":  3.0,  "expected": 1.0,  "desc": "하한 None → -∞"},
    {"min": 1.0,  "max": None, "r": 10.0,  "expected": 1.0,  "desc": "상한 None → +∞"},
    {"min": None, "max": None, "r":  3.0,  "expected": None,  "desc": "양쪽 None → skip"},
]

# ---------------------------------------------------------------------------
# score_chain  (실제 DB 샘플 기반)
# {"chain": dict, "v_m": float, "v_m1": float, "expected": dict, "desc": str}
# expected: {"r", "direction", "magnitude", "change_pct", "chain_score"}
# ---------------------------------------------------------------------------
CHAIN_CASES: list[dict] = [
    {
        "chain": {
            "causal_chain_id": "chain-001",
            "news_analysis_id": "na-001",
            "category": "oil",
            "direction": "up",
            "magnitude": "high",
            "change_pct_min": None,
            "change_pct_max": None,
        },
        # ecos_monthly import_price_crude_oil: 2025-03 → 2025-01 (하락 구간 역방향 테스트용)
        "v_m": 212.88, "v_m1": 235.96,
        "expected": {
            "r": 10.84,          # (235.96-212.88)/212.88*100 ≈ +10.84%
            "direction": 1.0,    # up 예측, R>1% → 실제 up ✓
            "magnitude": 1.0,    # high 예측, |R|≥7% → 실제 high ✓
            "change_pct": None,  # 범위 미설정 → skip
            "chain_score": 1.0,  # (1.0+1.0)/2
        },
        "desc": "oil 완전 적중 (change_pct 없음)",
    },
    {
        "chain": {
            "causal_chain_id": "chain-002",
            "news_analysis_id": "na-001",
            "category": "inflation",
            "direction": "up",
            "magnitude": "low",
            "change_pct_min": None,
            "change_pct_max": None,
        },
        # fred_monthly fred_cpi: 2026-01→02
        "v_m": 326.588, "v_m1": 327.46,
        "expected": {
            "r": 0.267,          # ≈ +0.267%
            "direction": 0.5,    # up vs 실제 neutral → partial (scorer.score_direction)
            "magnitude": 1.0,    # low 예측, |R|<2% → 실제 low ✓
            "change_pct": None,
            "chain_score": 0.6875,  # dir*0.625 + mag*0.375 (change_pct 없음)
        },
        "desc": "inflation: 방향 partial (neutral인데 up 예측), 강도 적중",
    },
    {
        "chain": {
            "causal_chain_id": "chain-003",
            "news_analysis_id": "na-002",
            "category": "food",
            "direction": "down",
            "magnitude": "medium",
            "change_pct_min": -5.0,
            "change_pct_max": -1.0,
        },
        # ecos_monthly import_price_food: 2025-01→02 (164.85→163.78)
        "v_m": 164.85, "v_m1": 163.78,
        "expected": {
            "r": -0.649,         # ≈ -0.65%
            "direction": 0.5,    # down vs 실제 neutral → partial
            "magnitude": 0.5,    # medium 예측, |R|<2% → 실제 low → 인접
            "change_pct": 0.0,   # R=-0.649%, 범위 [-5, -1] → 범위 밖
            "chain_score": 0.4,  # 0.5*0.5 + 0.5*0.3 + 0.0*0.2
        },
        "desc": "food: 방향 partial·범위 미스, 강도 인접",
    },
]
