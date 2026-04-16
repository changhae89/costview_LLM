"""Causal JSON parsing, normalization, and validation."""

from __future__ import annotations

import json
import re
from typing import Any

from prd.llm.chains.category_registry import (
    CATEGORY_FALLBACK_MAP,
    build_english_fallback_map,
    get_allowed_categories,
)
from prd.llm.schemas import CausalResult

ALLOWED_DIRECTIONS = {"up", "down", "neutral"}
ALLOWED_MAGNITUDES = {"low", "medium", "high"}
ALLOWED_INDICATORS = {"usd_krw", "wti", "gold", "base_rate"}
ALLOWED_TIME_HORIZONS = {"short", "medium", "long"}
ALLOWED_LEADING_INDICATORS = {"leading", "coincident", "lagging"}
ALLOWED_GEO_SCOPES = {"global", "asia", "korea"}
ALLOWED_ARTICLE_SCOPES = {
    "korea",
    "uk",
    "europe",
    "asia",
    "middle_east",
    "africa",
    "americas",
    "global",
    "unknown",
}
ALLOWED_KOREA_RELEVANCE = {"direct", "indirect", "none"}

MAGNITUDE_BANDS: dict[str, tuple[float, float]] = {
    "low": (0.0, 2.0),
    "medium": (2.0, 5.0),
    "high": (5.0, 10.0),
}
MACRO_PASS_THROUGH_CATEGORIES = {"price", "inflation", "cost"}
DEFAULT_DIRECTIONAL_LOW_BAND: tuple[float, float] = (0.5, 2.0)
MAX_DB_CHANGE_PCT = 999.99
MAX_DB_MONTHLY_IMPACT = 2_147_483_647

# 구 LLM/스키마에서 쓰이던 영어 라벨 → 현재 DB 코드
LEGACY_ENGLISH_CATEGORY_ALIASES: dict[str, str] = {
    "utility": "energy",
    "grocery": "food",
}


def parse_causal_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        body = "\n".join(lines[1:])
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3].rstrip()
        cleaned = body

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        cleaned = _flatten_json_strings(cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end <= start:
                raise ValueError("No JSON object found in model output.")
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"Failed to parse causal JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Causal output is not a JSON object.")
    return parsed


def normalize_causal(
    raw_causal: dict[str, Any],
    categories: list[str] | list[dict] | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    out = dict(raw_causal) if isinstance(raw_causal, dict) else {}
    raw_effects = out.get("effects")
    effects = raw_effects if isinstance(raw_effects, list) else []
    summary_cost_signal = _extract_summary_field(summary or "", "cost_signal").lower()
    raw_cats = categories or list(get_allowed_categories())
    allowed_categories = tuple(
        c["code"] if isinstance(c, dict) else c for c in raw_cats
    )
    normalized_effects: list[dict[str, Any]] = []

    for effect in effects:
        if not isinstance(effect, dict):
            continue
        category = _normalize_category(effect.get("category"), allowed_categories)
        if category is None:
            continue

        direction = _normalize_direction(effect.get("direction"))
        magnitude = _normalize_magnitude(effect.get("magnitude"))
        direction = _align_direction_with_cost_signal(direction, summary_cost_signal)
        change_pct_min = _to_float(effect.get("change_pct_min"))
        change_pct_max = _to_float(effect.get("change_pct_max"))
        monthly_impact = _to_int(effect.get("monthly_impact"))
        change_pct_min, change_pct_max = _normalize_change_pct_range(
            category=category,
            direction=direction,
            magnitude=magnitude,
            change_pct_min=change_pct_min,
            change_pct_max=change_pct_max,
        )
        magnitude = _derive_magnitude_from_range(
            direction=direction,
            change_pct_min=change_pct_min,
            change_pct_max=change_pct_max,
        )

        if direction == "neutral":
            magnitude = "low"
            change_pct_min = None
            change_pct_max = None
            monthly_impact = 0
        elif monthly_impact is None:
            monthly_impact = 0

        normalized_effects.append(
            {
                "category": category,
                "direction": direction,
                "magnitude": magnitude,
                "change_pct_min": change_pct_min,
                "change_pct_max": change_pct_max,
                "monthly_impact": monthly_impact,
            }
        )

    if summary_cost_signal == "none":
        normalized_effects = []
    else:
        normalized_effects = _reduce_zero_neutral_effects(normalized_effects, summary_cost_signal)

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for effect in normalized_effects:
        key = (
            effect["category"],
            effect["direction"],
            effect["magnitude"],
            effect["change_pct_min"],
            effect["change_pct_max"],
            effect["monthly_impact"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(effect)

    related_indicators = out.get("related_indicators")
    if isinstance(related_indicators, list):
        normalized_indicators = [
            str(item).strip()
            for item in related_indicators
            if str(item).strip() in ALLOWED_INDICATORS
        ]
    else:
        normalized_indicators = []

    # effect_chain: list[str]
    raw_chain = out.get("effect_chain")
    effect_chain = (
        [str(s).strip() for s in raw_chain if str(s).strip()]
        if isinstance(raw_chain, list)
        else []
    )

    normalized = {
        "event": str(out.get("event") or "").strip(),
        "mechanism": str(out.get("mechanism") or "").strip(),
        "related_indicators": normalized_indicators,
        "reliability": _normalize_reliability(out.get("reliability")),
        "reliability_reason": str(out.get("reliability_reason") or "").strip(),
        "effects": deduped,
        "time_horizon": _normalize_enum(out.get("time_horizon"), ALLOWED_TIME_HORIZONS),
        "effect_chain": effect_chain,
        "buffer": str(out.get("buffer") or "").strip(),
        "leading_indicator": _normalize_enum(out.get("leading_indicator"), ALLOWED_LEADING_INDICATORS),
        "geo_scope": _normalize_enum(out.get("geo_scope"), ALLOWED_GEO_SCOPES),
        "article_scope": _normalize_enum(out.get("article_scope"), ALLOWED_ARTICLE_SCOPES),
        "korea_relevance": _normalize_enum(out.get("korea_relevance"), ALLOWED_KOREA_RELEVANCE),
    }
    return CausalResult.model_validate(normalized).model_dump()


def validate_causal_result(causal: dict[str, Any], summary: str | None = None) -> None:
    event = str(causal.get("event") or "").strip()
    mechanism = str(causal.get("mechanism") or "").strip()
    effects = causal.get("effects") or []
    summary_cost_signal = _extract_summary_field(summary or "", "cost_signal").lower()

    if not event:
        raise ValueError("event is empty")
    if not mechanism:
        raise ValueError("mechanism is empty")
    if summary_cost_signal == "none" and effects:
        raise ValueError("effects must be empty when summary cost_signal is none")
    if summary_cost_signal in {"up", "down"}:
        for effect in effects:
            direction = str(effect.get("direction") or "").strip().lower()
            if direction in {"up", "down"} and direction != summary_cost_signal:
                raise ValueError(
                    f"effect direction {direction} conflicts with summary cost_signal {summary_cost_signal}"
                )

    if effects and _all_effects_are_zero_neutral(effects):
        raise ValueError("all effects are neutral with zero impact")



def _normalize_category(value: Any, allowed_categories: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in allowed_categories:
        return lowered
    legacy_target = LEGACY_ENGLISH_CATEGORY_ALIASES.get(lowered)
    if legacy_target and legacy_target in allowed_categories:
        return legacy_target
    raw = str(value).strip()
    # 한국어 fallback (코드 내 고정)
    for token, mapped in CATEGORY_FALLBACK_MAP.items():
        if token in raw and mapped in allowed_categories:
            return mapped
    # 영어 fallback (DB keywords 동적 생성)
    for token, mapped in build_english_fallback_map().items():
        if token in lowered and mapped in allowed_categories:
            return mapped
    return None


def _normalize_direction(value: Any) -> str:
    lowered = str(value or "neutral").strip().lower()
    if lowered in ALLOWED_DIRECTIONS:
        return lowered
    if lowered in {"increase", "rise", "higher", "상승", "인상", "증가", "오름"}:
        return "up"
    if lowered in {"decrease", "fall", "lower", "하락", "인하", "감소", "내림"}:
        return "down"
    return "neutral"


def _align_direction_with_cost_signal(direction: str, cost_signal: str) -> str:
    if cost_signal == "none":
        return "neutral"
    if direction == "neutral":
        return direction
    if cost_signal in {"up", "down"}:
        return cost_signal
    return direction


def _normalize_magnitude(value: Any) -> str:
    lowered = str(value or "medium").strip().lower()
    if lowered in ALLOWED_MAGNITUDES:
        return lowered
    if lowered in {"small", "minor", "낮음", "작음", "경미", "미미"}:
        return "low"
    if lowered in {"large", "strong", "높음", "큼", "강함", "심각"}:
        return "high"
    return "medium"


def _normalize_change_pct_range(
    *,
    category: str,
    direction: str,
    magnitude: str,
    change_pct_min: float | None,
    change_pct_max: float | None,
) -> tuple[float | None, float | None]:
    if direction == "neutral":
        return None, None

    band_min, band_max = MAGNITUDE_BANDS.get(magnitude, MAGNITUDE_BANDS["medium"])
    values = [abs(v) for v in (change_pct_min, change_pct_max) if v is not None]

    if not values:
        return None, None
    elif len(values) == 1:
        single = values[0]
        if single < band_min:
            values = [single, band_min]
        elif single > band_max:
            values = [band_min, single]
        else:
            values = [band_min, single]

    lo, hi = min(values), max(values)
    lo, hi = _snap_macro_categories_to_band(
        category=category,
        magnitude=magnitude,
        lo=lo,
        hi=hi,
    )
    lo = _clamp_change_pct(lo)
    hi = _clamp_change_pct(hi)

    if direction == "down":
        return -hi, -lo
    return lo, hi


def _snap_macro_categories_to_band(
    *,
    category: str,
    magnitude: str,
    lo: float,
    hi: float,
) -> tuple[float, float]:
    if category not in MACRO_PASS_THROUGH_CATEGORIES:
        return lo, hi
    if hi <= MAGNITUDE_BANDS["high"][1]:
        return lo, hi
    band_min, band_max = MAGNITUDE_BANDS.get(magnitude, MAGNITUDE_BANDS["medium"])
    return band_min, band_max


def _derive_magnitude_from_range(
    *,
    direction: str,
    change_pct_min: float | None,
    change_pct_max: float | None,
) -> str:
    if direction == "neutral":
        return "low"

    values = [abs(v) for v in (change_pct_min, change_pct_max) if v is not None]
    if not values:
        return "medium"

    peak = max(values)
    if peak >= MAGNITUDE_BANDS["high"][0]:
        return "high"
    if peak >= MAGNITUDE_BANDS["medium"][0]:
        return "medium"
    return "low"


def _normalize_enum(value: Any, allowed: set[str]) -> str | None:
    if value is None:
        return None
    lowered = str(value).strip().lower()
    return lowered if lowered in allowed else None


def _normalize_reliability(value: Any) -> float:
    raw = _to_float(value)
    if raw is None:
        return 0.85
    return max(0.0, min(1.0, raw))


def _reduce_zero_neutral_effects(
    effects: list[dict[str, Any]],
    summary_cost_signal: str,
) -> list[dict[str, Any]]:
    if summary_cost_signal not in {"up", "down"}:
        return effects
    if not effects or not _all_effects_are_zero_neutral(effects):
        return effects

    promoted: list[dict[str, Any]] = []
    promoted_once = False
    for effect in effects:
        updated = dict(effect)
        if not promoted_once:
            updated["direction"] = summary_cost_signal
            updated["magnitude"] = "low"
            if summary_cost_signal == "down":
                updated["change_pct_min"] = -DEFAULT_DIRECTIONAL_LOW_BAND[1]
                updated["change_pct_max"] = -DEFAULT_DIRECTIONAL_LOW_BAND[0]
            else:
                updated["change_pct_min"] = DEFAULT_DIRECTIONAL_LOW_BAND[0]
                updated["change_pct_max"] = DEFAULT_DIRECTIONAL_LOW_BAND[1]
            updated["monthly_impact"] = 0
            promoted_once = True
        promoted.append(updated)
    return promoted


def _extract_summary_field(summary: str, field_name: str) -> str:
    pattern = rf"(?im)^{re.escape(field_name)}:\s*(.+)$"
    match = re.search(pattern, summary or "")
    return match.group(1).strip() if match else ""


def _all_effects_are_zero_neutral(effects: list[dict[str, Any]]) -> bool:
    if not effects:
        return False
    for effect in effects:
        if str(effect.get("direction") or "").strip().lower() != "neutral":
            return False
        if _to_float(effect.get("change_pct_min")) not in (None, 0.0):
            return False
        if _to_float(effect.get("change_pct_max")) not in (None, 0.0):
            return False
        if _to_int(effect.get("monthly_impact")) not in (None, 0):
            return False
    return True


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return _clamp_change_pct(float(value))
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        raw = int(value)
        return max(-MAX_DB_MONTHLY_IMPACT, min(MAX_DB_MONTHLY_IMPACT, raw))
    except (TypeError, ValueError):
        return None


def _clamp_change_pct(value: float) -> float:
    return max(-MAX_DB_CHANGE_PCT, min(MAX_DB_CHANGE_PCT, value))


def _flatten_json_strings(text: str) -> str:
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == "\n":
            result.append(" ")
            continue
        result.append(ch)
    return "".join(result)
