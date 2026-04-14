"""History context builder for LLM prompt injection."""

from __future__ import annotations

from typing import Any


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
