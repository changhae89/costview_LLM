"""PostgreSQL implementation of NewsRepository."""

from __future__ import annotations

from prd.db.fetch import fetch_active_cost_categories, fetch_analysis_history, fetch_pending_news
from prd.db.save import mark_as_failed, mark_as_processed, mark_as_processing, save_analysis_result


class PostgresRepository:
    def __init__(self, connection) -> None:
        self._conn = connection

    def fetch_pending_news(self, limit: int) -> list[dict]:
        return fetch_pending_news(self._conn, limit=limit)

    def fetch_active_cost_categories(self) -> list[dict]:
        return fetch_active_cost_categories(self._conn)

    def fetch_analysis_history(
        self,
        *,
        current_news_id: str,
        keywords: list[str] | None,
        published_at: str | None,
        limit: int,
    ) -> list[dict]:
        return fetch_analysis_history(
            self._conn,
            current_news_id=current_news_id,
            keywords=keywords,
            published_at=published_at,
            limit=limit,
        )

    def save_analysis_result(self, news_id: str, result: dict) -> None:
        save_analysis_result(self._conn, news_id, result)

    def mark_as_processing(self, news_id: str) -> None:
        mark_as_processing(self._conn, news_id)

    def mark_as_processed(self, news_id: str) -> None:
        mark_as_processed(self._conn, news_id)

    def mark_as_failed(self, news_id: str, error_msg: str) -> None:
        mark_as_failed(self._conn, news_id, error_msg)

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()
