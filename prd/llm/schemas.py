from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Direction = Literal["up", "down", "neutral"]
Magnitude = Literal["low", "medium", "high"]
Indicator = Literal["usd_krw", "wti", "gold", "base_rate"]
TimeHorizon = Literal["short", "medium", "long"]
LeadingIndicatorType = Literal["leading", "coincident", "lagging"]
GeoScope = Literal["global", "asia", "korea"]


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
    reliability_reason: str = Field(default="")
    effects: list[CausalEffect] = Field(default_factory=list)
    time_horizon: TimeHorizon | None = None
    effect_chain: list[str] = Field(default_factory=list)
    buffer: str = Field(default="")
    leading_indicator: LeadingIndicatorType | None = None
    geo_scope: GeoScope | None = None


class NewsAnalysisResult(CausalResult):
    summary: str = Field(default="")
