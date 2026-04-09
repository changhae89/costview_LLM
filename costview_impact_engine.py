"""Deterministic CostView impact engine with optional Gemini text polishing.

This module is intentionally designed so that all business logic lives in Python.
Gemini is optional and only used to lightly polish already-determined text fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency path
    genai = None
    types = None


RISK_LEVEL_RULES: tuple[tuple[int, int, int], ...] = (
    (100, 119, 1),
    (120, 149, 2),
    (150, 199, 3),
    (200, 249, 4),
    (250, 10_000, 5),
)

BADGE_LABEL_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("밀", "소맥", "곡물"), "곡물 공급 불안"),
    (("원유", "가스", "석유"), "에너지 가격 상승"),
    (("철", "알루미늄", "니켈", "구리"), "원자재 가격 변동"),
)

GPR_CONTEXT_RULES: tuple[tuple[str, str], ...] = (
    ("항구 봉쇄", "수출 경로 차단으로 공급 감소가 발생했습니다."),
    ("가격 최고치", "국제 가격 급등으로 시장 불안이 확대되었습니다."),
    ("수출 제한", "주요 생산국의 수출 차질이 발생했습니다."),
)

CAUSE_DESCRIPTION_RULES: tuple[tuple[str, str], ...] = (
    ("항구 봉쇄", "수출 차질"),
    ("가격 최고치", "국제 가격 상승"),
)

SUBSTITUTE_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("밀", "소맥"), ("쌀", "감자", "고구마", "옥수수")),
    (("옥수수",), ("쌀", "감자")),
    (("원유",), ("두유", "식물성 대체식품")),
)

DEFAULT_SUBSTITUTES: tuple[str, str] = ("쌀", "감자")
DEFAULT_GPR_CONTEXT = "공급망 불안으로 가격 변동성이 확대되었습니다."
DEFAULT_CAUSE_DESCRIPTION = "공급 불안"
PRICE_DEFENSE_PHRASE = "가격이 방어되었습니다."
PRICE_DROP_PHRASE = "오히려 하락했습니다."
GEMINI_MODEL = "gemini-2.5-flash"
HEADLINE_MAX_LENGTH = 25


@dataclass(slots=True)
class ImpactInput:
    """Input payload for the CostView deterministic engine."""

    chain_id: str
    category: str
    event_name: str
    raw_material: str
    consumer_good: str
    cause_text: str
    event_date_text: str
    gpr_score: int | float
    lag_months: int
    consumer_price_change_pct: int | float
    base_item_name: str
    base_price: int


def validate_input(payload: ImpactInput) -> None:
    """Validate required input fields and raise ValueError when missing."""

    required_strings = {
        "chain_id": payload.chain_id,
        "category": payload.category,
        "event_name": payload.event_name,
        "raw_material": payload.raw_material,
        "consumer_good": payload.consumer_good,
        "cause_text": payload.cause_text,
        "event_date_text": payload.event_date_text,
        "base_item_name": payload.base_item_name,
    }
    for field_name, value in required_strings.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} is required.")

    if payload.lag_months < 0:
        raise ValueError("lag_months must be zero or greater.")
    if payload.base_price < 0:
        raise ValueError("base_price must be zero or greater.")


def determine_risk_level(gpr_score: int | float) -> int:
    """Map a GPR score to CostView risk level."""

    for minimum, maximum, level in RISK_LEVEL_RULES:
        if minimum <= gpr_score <= maximum:
            return level
    return 1


def determine_badge_label(raw_material: str) -> str:
    """Choose a deterministic badge label from raw material keywords."""

    for keywords, label in BADGE_LABEL_RULES:
        if any(keyword in raw_material for keyword in keywords):
            return label
    return "공급망 리스크 증가"


def build_gpr_context(cause_text: str) -> str:
    """Build deterministic GPR context text from cause keywords."""

    for keyword, template in GPR_CONTEXT_RULES:
        if keyword in cause_text:
            return template
    return DEFAULT_GPR_CONTEXT


def parse_event_date_text(event_date_text: str) -> tuple[int, int]:
    """Parse strings like '2022년 2월' into year and month."""

    match = re.search(r"(?P<year>\d{4})\s*년\s*(?P<month>\d{1,2})\s*월", event_date_text)
    if not match:
        raise ValueError("event_date_text must contain a 'YYYY년 M월' style date.")

    year = int(match.group("year"))
    month = int(match.group("month"))
    if month < 1 or month > 12:
        raise ValueError("Parsed month must be between 1 and 12.")
    return year, month


def add_months(year: int, month: int, lag_months: int) -> tuple[int, int]:
    """Add months to a year-month pair."""

    base_index = year * 12 + (month - 1)
    target_index = base_index + lag_months
    target_year = target_index // 12
    target_month = (target_index % 12) + 1
    return target_year, target_month


def format_korean_year_month(year: int, month: int) -> str:
    """Format a year-month pair as Korean text."""

    return f"{year}년 {month}월"


def build_warning_message(year: int, month: int) -> str:
    """Build deterministic warning message."""

    return f"{format_korean_year_month(year, month)}부터 관련 소비 지출 증가가 반영되기 시작합니다."


def build_real_world_example(item: str, base_price: int, pct: int | float) -> str:
    """Calculate price example using deterministic price math."""

    new_price = round(base_price * (1 + pct / 100))
    diff = round(base_price * (pct / 100))
    if pct >= 0:
        return f"{item} {base_price}원 기준 → 약 {new_price}원으로 상승 → 약 {diff}원 증가"
    return f"{item} {base_price}원 기준 → 약 {new_price}원으로 하락 → 약 {abs(diff)}원 감소"


def build_substitute_recommendations(raw_material: str) -> list[dict[str, str]]:
    """Pick the first matching substitute rule and return the first two items."""

    selected_candidates: tuple[str, ...] | None = None
    for keywords, candidates in SUBSTITUTE_RULES:
        if any(keyword in raw_material for keyword in keywords):
            selected_candidates = candidates
            break

    chosen_items = list(selected_candidates[:2] if selected_candidates else DEFAULT_SUBSTITUTES)
    return [
        {
            "item": item,
            "reason": f"{item}은 국내 생산 기반이 있어 수입 가격 변동 영향을 상대적으로 덜 받습니다.",
        }
        for item in chosen_items
    ]


def determine_cause_description(cause_text: str) -> str:
    """Map cause text to storytelling cause phrase."""

    for keyword, description in CAUSE_DESCRIPTION_RULES:
        if keyword in cause_text:
            return description
    return DEFAULT_CAUSE_DESCRIPTION


def shorten_headline(headline: str, max_length: int = HEADLINE_MAX_LENGTH) -> str:
    """Shorten headline to a compact length without breaking execution."""

    if len(headline) <= max_length:
        return headline

    compact = headline.replace(" 영향 확대", "").replace(" 가격", "").strip()
    if len(compact) <= max_length:
        return compact

    return compact[: max_length - 1].rstrip() + "…"


def build_storytelling_description(
    cause_text: str,
    raw_material: str,
    consumer_good: str,
    pct: int | float,
) -> str:
    """Build a deterministic storytelling description with fallback phrasing."""

    cause_description = determine_cause_description(cause_text)
    if pct == 0:
        return (
            f"{cause_description}에도 {raw_material} 가격이 방어되며 "
            f"{consumer_good} 가격이 안정적으로 유지되었습니다. {PRICE_DEFENSE_PHRASE}"
        )
    if pct < 0:
        return (
            f"{cause_description} 이후 {raw_material} 가격이 조정되며 "
            f"{consumer_good} 가격이 오히려 하락했습니다. {PRICE_DROP_PHRASE}"
        )
    return f"{cause_description}으로 {raw_material} 가격이 상승하며 {consumer_good} 가격에 반영되었습니다."


class CostViewGeminiFormatter:
    """Optional Gemini formatter limited to polishing already-determined text."""

    def __init__(self, api_key: str, model: str = GEMINI_MODEL) -> None:
        """Initialize Gemini client."""

        if not api_key.strip():
            raise ValueError("api_key is required when use_llm=True.")
        if genai is None or types is None:
            raise RuntimeError(
                "The google-genai package is not installed. Install it before using use_llm=True."
            )

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def polish_text(self, text: str, purpose: str) -> str:
        """Polish text while preserving business meaning and numbers."""

        prompt = (
            "다음 문장을 한국어로 자연스럽게 다듬어라. "
            "숫자, 날짜, 방향성, 의미를 바꾸지 말고 한 문장으로만 출력하라.\n"
            f"용도: {purpose}\n"
            f"원문: {text}"
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=120,
            ),
        )
        polished = (response.text or "").strip()
        return polished or text


class CostViewImpactEngine:
    """Deterministic engine for building CostView impact-chain payloads."""

    def __init__(self, gemini_formatter: CostViewGeminiFormatter | None = None) -> None:
        """Initialize engine with optional Gemini formatter."""

        self._gemini_formatter = gemini_formatter

    def analyze_impact_chain(self, payload: ImpactInput, use_llm: bool = False) -> dict[str, Any]:
        """Build the full CostView output schema from deterministic Python rules."""

        validate_input(payload)

        risk_level = determine_risk_level(payload.gpr_score)
        badge_label = determine_badge_label(payload.raw_material)
        gpr_context = build_gpr_context(payload.cause_text)

        event_year, event_month = parse_event_date_text(payload.event_date_text)
        impact_year, impact_month = add_months(event_year, event_month, payload.lag_months)
        warning_message = build_warning_message(impact_year, impact_month)

        real_world_example = build_real_world_example(
            item=payload.base_item_name,
            base_price=payload.base_price,
            pct=payload.consumer_price_change_pct,
        )

        substitutes = build_substitute_recommendations(payload.raw_material)

        headline = shorten_headline(f"{payload.raw_material} 가격 상승 영향 확대")
        description = build_storytelling_description(
            cause_text=payload.cause_text,
            raw_material=payload.raw_material,
            consumer_good=payload.consumer_good,
            pct=payload.consumer_price_change_pct,
        )

        if use_llm and self._gemini_formatter is not None:
            try:
                gpr_context = self._gemini_formatter.polish_text(
                    gpr_context,
                    purpose="gpr_context",
                )
                description = self._gemini_formatter.polish_text(
                    description,
                    purpose="storytelling.description",
                )
            except Exception:
                # Deterministic Python output remains the fallback.
                pass

        return {
            "chain_id": payload.chain_id,
            "category": payload.category,
            "event_name": payload.event_name,
            "raw_material": payload.raw_material,
            "consumer_good": payload.consumer_good,
            "risk_assessment": {
                "level": risk_level,
                "badge_label": badge_label,
                "gpr_context": gpr_context,
            },
            "timing_forecast": {
                "lag_months": payload.lag_months,
                "warning_message": warning_message,
            },
            "tangible_impact": {
                "consumer_price_change_pct": payload.consumer_price_change_pct,
                "real_world_example": real_world_example,
            },
            "substitute_recommendations": substitutes,
            "storytelling": {
                "headline": headline,
                "description": description,
            },
        }


if __name__ == "__main__":
    example_input = ImpactInput(
        chain_id="CHN_RUA_001",
        category="식품",
        event_name="러시아-우크라이나 전쟁",
        raw_material="국제 소맥(밀)",
        consumer_good="국내 빵/면류",
        cause_text="항구 봉쇄와 가격 최고치가 동시에 발생",
        event_date_text="2022년 2월",
        gpr_score=280,
        lag_months=4,
        consumer_price_change_pct=11.4,
        base_item_name="식빵 1봉지",
        base_price=2000,
    )

    engine = CostViewImpactEngine()
    result = engine.analyze_impact_chain(example_input, use_llm=False)
    print(result)
