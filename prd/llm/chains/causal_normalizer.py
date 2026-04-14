"""Causal JSON parsing, normalization, and validation."""

from __future__ import annotations

import json
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


def normalize_causal(raw_causal: dict[str, Any], categories: list[str] | list[dict] | None = None) -> dict[str, Any]:
    out = dict(raw_causal) if isinstance(raw_causal, dict) else {}
    raw_effects = out.get("effects")
    effects = raw_effects if isinstance(raw_effects, list) else []
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
        change_pct_min = _to_float(effect.get("change_pct_min"))
        change_pct_max = _to_float(effect.get("change_pct_max"))
        monthly_impact = _to_int(effect.get("monthly_impact"))

        if (
            direction == "neutral"
            and (change_pct_min in (None, 0.0))
            and (change_pct_max in (None, 0.0))
            and (monthly_impact in (None, 0))
        ):
            magnitude = "low"

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

    normalized = {
        "event": str(out.get("event") or "").strip(),
        "mechanism": str(out.get("mechanism") or "").strip(),
        "related_indicators": normalized_indicators,
        "reliability": _normalize_reliability(out.get("reliability")),
        "effects": deduped,
    }
    return CausalResult.model_validate(normalized).model_dump()


def validate_causal_result(causal: dict[str, Any]) -> None:
    event = str(causal.get("event") or "").strip()
    mechanism = str(causal.get("mechanism") or "").strip()
    effects = causal.get("effects") or []

    if not event:
        raise ValueError("event is empty")
    if not mechanism:
        raise ValueError("mechanism is empty")

    if effects and _all_effects_are_zero_neutral(effects):
        raise ValueError("all effects are neutral with zero impact")

    if not effects and float(causal.get("reliability") or 0) > 0.95:
        raise ValueError("empty effects with implausibly high reliability")


def _normalize_category(value: Any, allowed_categories: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in allowed_categories:
        return lowered
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


def _normalize_magnitude(value: Any) -> str:
    lowered = str(value or "medium").strip().lower()
    if lowered in ALLOWED_MAGNITUDES:
        return lowered
    if lowered in {"small", "minor", "낮음", "작음", "경미", "미미"}:
        return "low"
    if lowered in {"large", "strong", "높음", "큼", "강함", "심각"}:
        return "high"
    return "medium"


def _normalize_reliability(value: Any) -> float:
    raw = _to_float(value)
    if raw is None:
        return 0.85
    return max(0.0, min(1.0, raw))


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
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


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
