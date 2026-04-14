from prd.llm.chains.causal_normalizer import (
    normalize_causal,
    parse_causal_json,
    validate_causal_result,
)
from prd.llm.chains.category_registry import get_allowed_categories
from prd.llm.chains.history_builder import build_history_context
from prd.llm.chains.llm_runner import _is_retryable_error


def test_parse_causal_json_extracts_object_from_code_fence() -> None:
    raw = """```json
    {
      "event": "oil price rise",
      "mechanism": "transport cost increase",
      "related_indicators": ["wti"],
      "reliability": 0.8,
      "effects": [
        {
          "category": "fuel",
          "direction": "up",
          "magnitude": "medium",
          "change_pct_min": 1.5,
          "change_pct_max": 3.0,
          "monthly_impact": 20000
        }
      ]
    }
    ```"""
    parsed = parse_causal_json(raw)
    assert parsed["event"] == "oil price rise"
    assert parsed["effects"][0]["category"] == "fuel"


def test_normalize_causal_filters_invalid_values() -> None:
    normalized = normalize_causal(
        {
            "event": "exchange rate move",
            "mechanism": "import costs change",
            "related_indicators": ["usd_krw", "invalid_indicator"],
            "reliability": 5,
            "effects": [
                {
                    "category": "fuel",
                    "direction": "increase",
                    "magnitude": "large",
                    "change_pct_min": "1.2",
                    "change_pct_max": "2.4",
                    "monthly_impact": "15000",
                },
                {
                    "category": "unknown",
                    "direction": "up",
                    "magnitude": "high",
                },
            ],
        }
    )
    assert normalized["related_indicators"] == ["usd_krw"]
    assert normalized["reliability"] == 1.0
    assert len(normalized["effects"]) == 1
    assert normalized["effects"][0]["direction"] == "up"
    assert normalized["effects"][0]["magnitude"] == "high"


def test_normalize_causal_maps_legacy_categories_to_db_categories() -> None:
    normalized = normalize_causal(
        {
            "event": "energy price move",
            "mechanism": "utility costs move",
            "related_indicators": [],
            "reliability": 0.7,
            "effects": [
                {"category": "utility", "direction": "down", "magnitude": "low"},
                {"category": "grocery", "direction": "up", "magnitude": "medium"},
            ],
        }
    )
    assert normalized["effects"][0]["category"] == "energy"
    assert normalized["effects"][1]["category"] == "food"


def test_is_retryable_error_matches_transient_messages() -> None:
    assert _is_retryable_error(RuntimeError("429 resource exhausted"))
    assert _is_retryable_error(RuntimeError("Service unavailable"))
    assert not _is_retryable_error(RuntimeError("invalid api key"))


def test_build_history_context_formats_history_items() -> None:
    text = build_history_context(
        [
            {
                "title": "과거 기사",
                "published_at": "2026-04-10T00:00:00Z",
                "summary": "과거 요약입니다.",
                "reliability": 0.8,
                "related_indicators": ["wti"],
                "effects": [
                    {
                        "category": "fuel",
                        "direction": "down",
                        "magnitude": "low",
                        "monthly_impact": 2000,
                    }
                ],
            }
        ]
    )
    assert "[과거 분석 뉴스 컨텍스트]" in text
    assert "요약: 과거 요약입니다." in text
    assert "영향: fuel/down/low/2000" in text


def test_get_allowed_categories_has_cost_category_codes() -> None:
    categories = get_allowed_categories()
    codes = {c["code"] for c in categories}
    assert "oil" in codes
    assert "shipping" in codes


def test_validate_causal_result_rejects_empty_event_and_mechanism() -> None:
    try:
        validate_causal_result(
            {
                "event": "",
                "mechanism": "",
                "related_indicators": [],
                "reliability": 0.8,
                "effects": [],
            }
        )
    except ValueError as exc:
        assert "event is empty" in str(exc)
    else:
        raise AssertionError("validate_causal_result should reject empty event/mechanism")


def test_validate_causal_result_rejects_zero_neutral_only_effects() -> None:
    try:
        validate_causal_result(
            {
                "event": "energy outlook",
                "mechanism": "unclear market reaction",
                "related_indicators": [],
                "reliability": 0.7,
                "effects": [
                    {
                        "category": "energy",
                        "direction": "neutral",
                        "magnitude": "low",
                        "change_pct_min": 0,
                        "change_pct_max": 0,
                        "monthly_impact": 0,
                    }
                ],
            }
        )
    except ValueError as exc:
        assert "all effects are neutral with zero impact" in str(exc)
    else:
        raise AssertionError("validate_causal_result should reject zero-neutral-only effects")
