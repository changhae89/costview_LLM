"""Supabase implementation of NewsRepository."""

from __future__ import annotations

from typing import Any

from prd.db.supabase_store import (
    fetch_active_cost_categories_sb,
    fetch_analysis_history_sb,
    fetch_indicators_by_date_sb,
    fetch_pending_news_sb,
    mark_as_failed_sb,
    mark_as_processed_sb,
    mark_as_processing_sb,
    mark_as_skipped_sb,
    save_analysis_result_sb,
)


class SupabaseRepository:
    def __init__(self, client: Any) -> None:
        self._sb = client

    def fetch_pending_news(self, limit: int) -> list[dict]:
        return fetch_pending_news_sb(self._sb, limit=limit)

    def fetch_active_cost_categories(self) -> list[dict]:
        return fetch_active_cost_categories_sb(self._sb)

    def fetch_analysis_history(
        self,
        *,
        current_news_id: str,
        keywords: list[str] | None,
        published_at: str | None,
        limit: int,
    ) -> list[dict]:
        return fetch_analysis_history_sb(
            self._sb,
            current_news_id=current_news_id,
            keywords=keywords,
            published_at=published_at,
            limit=limit,
        )

    def fetch_indicators_by_date(self, *, reference_date: str) -> dict:
        return fetch_indicators_by_date_sb(self._sb, reference_date=reference_date)

    def save_analysis_result(self, news_id: str, result: dict) -> None:
        save_analysis_result_sb(self._sb, news_id, result)

    def mark_as_processing(self, news_id: str) -> None:
        mark_as_processing_sb(self._sb, news_id)

    def mark_as_processed(self, news_id: str) -> None:
        mark_as_processed_sb(self._sb, news_id)

    def mark_as_skipped(self, news_id: str) -> None:
        mark_as_skipped_sb(self._sb, news_id)

    def mark_as_failed(self, news_id: str, error_msg: str) -> None:
        mark_as_failed_sb(self._sb, news_id, error_msg)

    def rollback(self) -> None:
        pass  # Supabase는 트랜잭션 롤백 불필요

    def close(self) -> None:
        pass  # Supabase 클라이언트는 명시적 종료 불필요
