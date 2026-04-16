"""Scoring parameters for validation backtest.

All thresholds apply to R = MoM % change = (v_m1 - v_m) / |v_m| * 100.
"""

# Direction: realized is "neutral" when |R| is below this (%)
NEUTRAL_THRESHOLD_PCT: float = 1.0

# Magnitude bucket boundaries (%)
#   |R| < LOW_MAX              → low
#   LOW_MAX <= |R| < HIGH_MIN  → medium
#   |R| >= HIGH_MIN            → high
MAGNITUDE_LOW_MAX_PCT: float = 2.0
MAGNITUDE_HIGH_MIN_PCT: float = 5.0

# change_pct range inclusivity: True = [min, max] both inclusive
CHANGE_PCT_INCLUSIVE: bool = True

# 시차 검증: M+N 으로 비교할 개월 수 (1 = M+1, 2 = M+2, ...)
HORIZON_MONTHS: int = 1
