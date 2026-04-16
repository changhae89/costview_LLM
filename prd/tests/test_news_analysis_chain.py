from prd.llm.graph.news_pipeline_graph import (
    _cost_signal_is_core_topic,
    _extract_summary_field,
    _summary_has_grounding_issue,
    _summary_has_minimum_format,
    pre_filter_node,
)
from prd.llm.chains.causal_normalizer import (
    normalize_causal,
    parse_causal_json,
    validate_causal_result,
)
from prd.llm.chains.category_registry import get_allowed_categories
from prd.llm.chains.history_builder import build_history_context
from prd.llm.chains.llm_runner import _is_retryable_error
from prd.llm.prompts.causal_prompt import build_causal_prompt


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


def test_build_causal_prompt_formats_messages_without_brace_errors() -> None:
    prompt = build_causal_prompt(
        [{"code": "fuel", "name_ko": "연료", "keywords": ["petrol", "diesel"]}]
    )
    messages = prompt.format_messages(
        summary="event: oil rise\ncost_signal: up\nconsumer_link: yes\nfacts: petrol price up",
        indicator_context="date: 2024-01-01",
        history_context="없음",
    )
    assert len(messages) == 2


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


def test_summary_minimum_format_requires_all_fields() -> None:
    broken = "event: test\ncost_signal: none\nfacts: missing consumer link"
    assert not _summary_has_minimum_format(broken)
    assert _extract_summary_field(broken, "consumer_link") == ""


def test_summary_grounding_flags_missing_numbers_and_inflation_terms() -> None:
    content = "The article is about intellectual property tax relief for 3G licences and goodwill."
    summary = (
        "event: 영국 인플레이션 급등\n"
        "cost_signal: up\n"
        "facts: 지난 한 해 동안 가격이 20% 상승\n"
        "consumer_link: yes"
    )
    assert _summary_has_grounding_issue(content, summary) is True


def test_summary_grounding_allows_supported_numbers() -> None:
    content = "The budget raised petrol duties and made petrol the most expensive in Europe by 5%."
    summary = (
        "event: 휘발유 세금 인상\n"
        "cost_signal: up\n"
        "facts: 휘발유 세금이 5% 올라 가격 부담이 커짐\n"
        "consumer_link: yes"
    )
    assert _summary_has_grounding_issue(content, summary) is False


def test_cost_signal_core_topic_rejects_market_article_with_cpi_side_note() -> None:
    title = "Drugs are anti-depressant"
    content = (
        "The FTSE 100 recovered after stronger than expected US consumer prices data. "
        "Leading shares, Nasdaq moves, broker ratings and telecom stocks dominated the session."
    )
    summary = (
        "event: 미국 소매 인플레이션 데이터 발표\n"
        "cost_signal: up\n"
        "facts: 미국 소비자 물가 상승\n"
        "consumer_link: yes"
    )
    assert _cost_signal_is_core_topic(title, content, summary) is False


def test_cost_signal_core_topic_accepts_direct_petrol_tax_article() -> None:
    title = "Blair defends petrol price rises"
    content = (
        "The budget raised petrol duties and increased fuel costs for drivers. "
        "The debate focused on petrol prices and household fuel burden."
    )
    summary = (
        "event: 휘발유 세금 인상\n"
        "cost_signal: up\n"
        "facts: 예산에서 휘발유 세금이 인상됨\n"
        "consumer_link: yes"
    )
    assert _cost_signal_is_core_topic(title, content, summary) is True


def test_pre_filter_skips_scoped_articles_without_direct_cost_signal() -> None:
    state = {
        "news": {
            "title": "Smart money sees a future for sterling",
            "content": "Debate on EMU, CPI, exchange rates and central bank policy dominates the article.",
            "keyword": [],
            "allowed_categories": [{"code": "fuel", "name_ko": "연료", "keywords": ["petrol"]}],
        }
    }
    result = pre_filter_node(state)
    assert result["result"]["_skip"] is True
    assert result["result"]["reliability_reason"] == "No direct consumer-cost signal detected in scoped run."


def test_pre_filter_allows_scoped_articles_with_direct_cost_signal() -> None:
    state = {
        "news": {
            "title": "Blair defends petrol price rises",
            "content": "The budget raised petrol duties and increased fuel costs for drivers.",
            "keyword": [],
            "allowed_categories": [{"code": "fuel", "name_ko": "연료", "keywords": ["petrol"]}],
        }
    }
    result = pre_filter_node(state)
    assert "result" not in result


def test_pre_filter_skips_scoped_bio_patent_article() -> None:
    state = {
        "news": {
            "title": "Gold rush",
            "content": "Biotech firms seek patent protection on genes while CPI and monetary policy are debated.",
            "keyword": [],
            "allowed_categories": [{"code": "food", "name_ko": "식품", "keywords": ["food"]}],
        }
    }
    result = pre_filter_node(state)
    assert result["result"]["_skip"] is True
    assert result["result"]["reliability_reason"] == "No direct consumer-cost signal detected in scoped run."
