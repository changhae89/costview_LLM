"""NewsRepository protocol — shared interface for PostgreSQL and Supabase backends."""

from __future__ import annotations

from typing import Protocol


class NewsRepository(Protocol):
    def fetch_pending_news(self, limit: int) -> list[dict]: ...

    def fetch_active_cost_categories(self) -> list[dict]: ...

    def fetch_analysis_history(
        self,
        *,
        current_news_id: str,
        keywords: list[str] | None,
        published_at: str | None,
        limit: int,
    ) -> list[dict]: ...

    def fetch_indicators_by_date(self, *, reference_date: str) -> dict: ...

    def save_analysis_result(self, news_id: str, result: dict) -> None: ...

    def mark_as_processing(self, news_id: str) -> None: ...

    def mark_as_processed(self, news_id: str) -> None: ...

    def mark_as_skipped(self, news_id: str) -> None: ...

    def mark_as_failed(self, news_id: str, error_msg: str) -> None: ...
