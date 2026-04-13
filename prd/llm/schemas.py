from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Direction = Literal["up", "down", "neutral"]
Magnitude = Literal["low", "medium", "high"]
Indicator = Literal["usd_krw", "wti", "gold", "base_rate"]


class CausalEffect(BaseModel):
    category: str
    direction: Direction
    magnitude: Magnitude
    change_pct_min: float | None = None
    change_pct_max: float | None = None
    monthly_impact: int | None = None


class CausalResult(BaseModel):
    event: str = Field(default="")
    mechanism: str = Field(default="")
    related_indicators: list[Indicator] = Field(default_factory=list)
    reliability: float = 0.85
    effects: list[CausalEffect] = Field(default_factory=list)


class NewsAnalysisResult(CausalResult):
    summary: str = Field(default="")
