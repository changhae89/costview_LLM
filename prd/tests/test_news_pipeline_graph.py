import pytest

from prd.llm.graph import news_pipeline_graph as graph_module


@pytest.mark.asyncio
async def test_analyze_news_repairs_invalid_json(monkeypatch) -> None:
    async def fake_summary(_: str) -> str:
        return "요약 첫 문장. 요약 두 번째 문장. 요약 세 번째 문장."

    async def fake_causal(_: str, __: str = "없음", categories=None) -> str:
        return "not-json"

    async def fake_repair(_: str, __: str) -> str:
        return """
        {
          "event": "oil reserve release",
          "mechanism": "supply pressure eases",
          "related_indicators": ["wti"],
          "reliability": 0.8,
          "effects": [
            {
              "category": "fuel",
              "direction": "down",
              "magnitude": "low",
              "change_pct_min": 0.5,
              "change_pct_max": 1.0,
              "monthly_impact": -5000
            }
          ]
        }
        """

    monkeypatch.setattr(graph_module, "run_summary_chain", fake_summary)
    monkeypatch.setattr(graph_module, "run_causal_chain", fake_causal)
    monkeypatch.setattr(graph_module, "run_repair_chain", fake_repair)

    result = await graph_module.analyze_news(
        {
            "id": "n1",
            "title": "oil news",
            "content": "oil reserve story",
            "history_items": [],
            "allowed_categories": ["oil", "fuel", "energy"],
        }
    )

    assert result["summary"].startswith("요약 첫 문장")
    assert result["related_indicators"] == ["wti"]
    assert result["effects"][0]["category"] == "fuel"
    assert result["effects"][0]["direction"] == "down"


@pytest.mark.asyncio
async def test_analyze_news_fails_after_max_repairs(monkeypatch) -> None:
    async def fake_summary(_: str) -> str:
        return "요약 첫 문장. 요약 두 번째 문장. 요약 세 번째 문장."

    async def fake_causal(_: str, __: str = "없음", categories=None) -> str:
        return "not-json"

    async def fake_repair(_: str, __: str) -> str:
        return "still-not-json"

    monkeypatch.setattr(graph_module, "run_summary_chain", fake_summary)
    monkeypatch.setattr(graph_module, "run_causal_chain", fake_causal)
    monkeypatch.setattr(graph_module, "run_repair_chain", fake_repair)

    with pytest.raises(
        ValueError,
        match="stage=validate_causal attempts=3 error=No JSON object found in model output.",
    ):
        await graph_module.analyze_news(
            {
                "id": "n2",
                "title": "broken news",
                "content": "broken content",
                "history_items": [],
                "allowed_categories": ["oil", "fuel", "energy"],
            }
        )


@pytest.mark.asyncio
async def test_analyze_news_retries_when_zero_neutral_only_output(monkeypatch) -> None:
    async def fake_summary(_: str) -> str:
        return "요약 첫 문장. 요약 두 번째 문장. 요약 세 번째 문장."

    async def fake_causal(_: str, __: str = "없음", categories=None) -> str:
        return """
        {
          "event": "",
          "mechanism": "",
          "related_indicators": [],
          "reliability": 0.85,
          "effects": [
            {
              "category": "energy",
              "direction": "neutral",
              "magnitude": "low",
              "change_pct_min": 0,
              "change_pct_max": 0,
              "monthly_impact": 0
            }
          ]
        }
        """

    async def fake_repair(_: str, __: str) -> str:
        return """
        {
          "event": "energy outlook revision",
          "mechanism": "direct household-cost impact is unclear",
          "related_indicators": [],
          "reliability": 0.55,
          "effects": []
        }
        """

    monkeypatch.setattr(graph_module, "run_summary_chain", fake_summary)
    monkeypatch.setattr(graph_module, "run_causal_chain", fake_causal)
    monkeypatch.setattr(graph_module, "run_repair_chain", fake_repair)

    result = await graph_module.analyze_news(
        {
            "id": "n3",
            "title": "unclear energy news",
            "content": "unclear energy content",
            "history_items": [],
            "allowed_categories": ["oil", "fuel", "energy"],
        }
    )

    assert result["event"] == "energy outlook revision"
    assert result["mechanism"] == "direct household-cost impact is unclear"
    assert result["effects"] == []
