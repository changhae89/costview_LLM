from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from prd.config import get_gemini_api_key, get_gemini_model
from prd.db.connection import get_connection
from prd.db.fetch import fetch_active_cost_categories
from prd.llm.prompts.causal_prompt import build_causal_prompt
from prd.llm.prompts.repair_prompt import REPAIR_PROMPT
from prd.llm.prompts.summary_prompt import SUMMARY_PROMPT
from prd.llm.schemas import CausalResult

MAX_MODEL_RETRIES = 3
RETRYABLE_ERROR_MARKERS = (
    "429",
    "quota",
    "resource exhausted",
    "deadline exceeded",
    "temporarily unavailable",
    "service unavailable",
    "internal",
    "timeout",
    "connection reset",
)
DEFAULT_ALLOWED_CATEGORIES = (
    "oil",
    "fuel",
    "gas",
    "energy",
    "food",
    "wheat",
    "commodity",
    "price",
    "cost",
    "inflation",
    "shipping",
)
ALLOWED_DIRECTIONS = {"up", "down", "neutral"}
ALLOWED_MAGNITUDES = {"low", "medium", "high"}
ALLOWED_INDICATORS = {"usd_krw", "wti", "gold", "base_rate"}

CATEGORY_FALLBACK_MAP = {
    "원유": "oil",
    "유가": "oil",
    "배럴": "oil",
    "opec": "oil",
    "주유": "fuel",
    "휘발유": "fuel",
    "경유": "fuel",
    "디젤": "fuel",
    "가스": "gas",
    "난방": "gas",
    "lng": "gas",
    "전기": "energy",
    "전력": "energy",
    "에너지": "energy",
    "장보기": "food",
    "마트": "food",
    "식료": "food",
    "외식": "food",
    "식당": "food",
    "쌀": "wheat",
    "밀": "wheat",
    "곡물": "wheat",
    "농산물": "wheat",
    "원자재": "commodity",
    "잡화": "commodity",
    "의류": "commodity",
    "옷": "commodity",
    "물가": "price",
    "소비자가격": "price",
    "생활비": "cost",
    "가계": "cost",
    "대출": "cost",
    "금리": "cost",
    "이자": "cost",
    "인플레": "inflation",
    "물가상승": "inflation",
    "물류": "shipping",
    "운송": "shipping",
    "택배": "shipping",
    "항공": "shipping",
    "여행": "shipping",
    "grocery": "food",
    "dining": "food",
    "utility": "energy",
    "logistics": "shipping",
    "transport": "shipping",
}


def _create_model(*, temperature: float, max_tokens: int) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        google_api_key=get_gemini_api_key(),
        temperature=temperature,
        max_output_tokens=max_tokens,
    )


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(part.strip() for part in parts if part).strip()
    return str(content).strip()


def _print_chain_prompt(label: str, prompt: Any, payload: dict[str, Any]) -> None:
    try:
        messages = prompt.format_messages(**payload)
    except Exception:
        return

    for message in messages:
        role = getattr(message, "type", "message").upper()
        text = _message_text(message)
        print(f"[{label}] --- {role} PROMPT START ---")
        print(text)
        print(f"[{label}] --- {role} PROMPT END ---")


async def run_summary_chain(content: str) -> str:
    payload = {"content": content[:4000]}
    _print_chain_prompt("LLM1", SUMMARY_PROMPT, payload)
    text = await _invoke_chain(
        SUMMARY_PROMPT,
        payload,
        temperature=0.2,
        max_tokens=768,
    )
    if not text:
        raise ValueError("Summary chain returned an empty response.")
    return text


async def run_causal_chain(summary: str, history_context: str = "없음", categories: list[str] | None = None) -> str:
    allowed_categories = categories or list(get_allowed_categories())
    text = await _invoke_chain(
        build_causal_prompt(allowed_categories),
        {"summary": summary, "history_context": history_context},
        temperature=0.15,
        max_tokens=2048,
    )
    if not text:
        raise ValueError("Causal chain returned an empty response.")
    return text


async def run_repair_chain(summary: str, causal_raw: str) -> str:
    text = await _invoke_chain(
        REPAIR_PROMPT,
        {"summary": summary, "causal_raw": causal_raw[:4000]},
        temperature=0.1,
        max_tokens=2048,
    )
    if not text:
        raise ValueError("Repair chain returned an empty response.")
    return text


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


def normalize_causal(raw_causal: dict[str, Any], categories: list[str] | None = None) -> dict[str, Any]:
    out = dict(raw_causal) if isinstance(raw_causal, dict) else {}
    raw_effects = out.get("effects")
    effects = raw_effects if isinstance(raw_effects, list) else []
    allowed_categories = tuple(categories or get_allowed_categories())
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
    for token, mapped in CATEGORY_FALLBACK_MAP.items():
        if token in raw and mapped in allowed_categories:
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


async def _invoke_chain(
    prompt: Any,
    payload: dict[str, Any],
    *,
    temperature: float,
    max_tokens: int,
) -> str:
    chain = prompt | _create_model(temperature=temperature, max_tokens=max_tokens)
    last_error: Exception | None = None

    for attempt in range(1, MAX_MODEL_RETRIES + 1):
        try:
            response = await chain.ainvoke(payload)
            return _message_text(response)
        except Exception as exc:
            last_error = exc
            if attempt >= MAX_MODEL_RETRIES or not _is_retryable_error(exc):
                raise
            await asyncio.sleep(0.8 * attempt)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Chain invocation failed without a captured exception.")


def _is_retryable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in RETRYABLE_ERROR_MARKERS)


@lru_cache(maxsize=1)
def get_allowed_categories() -> tuple[str, ...]:
    try:
        connection = get_connection()
    except Exception:
        return DEFAULT_ALLOWED_CATEGORIES

    try:
        categories = fetch_active_cost_categories(connection)
        return tuple(categories) if categories else DEFAULT_ALLOWED_CATEGORIES
    except Exception:
        return DEFAULT_ALLOWED_CATEGORIES
    finally:
        connection.close()


def build_history_context(history_items: list[dict[str, Any]] | None) -> str:
    if not history_items:
        return "없음"

    chunks: list[str] = ["[과거 분석 뉴스 컨텍스트]"]
    for idx, item in enumerate(history_items, start=1):
        effects = item.get("effects") or []
        if effects:
            effect_text = "; ".join(
                (
                    f"{effect.get('category')}/{effect.get('direction')}/"
                    f"{effect.get('magnitude')}/{effect.get('monthly_impact')}"
                )
                for effect in effects
                if effect.get("category")
            )
        else:
            effect_text = "영향 없음"

        chunks.append(
            "\n".join(
                [
                    f"{idx}. 제목: {item.get('title') or ''}",
                    f"발행시각: {item.get('published_at') or ''}",
                    f"요약: {(item.get('summary') or '')[:240]}",
                    f"신뢰도: {item.get('reliability')}",
                    f"지표: {', '.join(item.get('related_indicators') or []) or '없음'}",
                    f"영향: {effect_text}",
                ]
            )
        )
    return "\n\n".join(chunks)


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
