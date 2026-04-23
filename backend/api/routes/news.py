from fastapi import APIRouter, Depends

from auth import require_auth
from db import get_conn

router = APIRouter(dependencies=[Depends(require_auth)])


def _rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@router.get("/raw")
def list_raw_news(
    page: int = 0,
    page_size: int = 50,
    status: list[str] | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    show_deleted: bool = False,
):
    where = []
    params: list[object] = []
    if not show_deleted:
        where.append("is_deleted = false")
    if status:
        where.append("processing_status = ANY(%s)")
        params.append(status)
    if search:
        where.append("title ILIKE %s")
        params.append(f"%{search}%")
    if date_from:
        where.append("origin_published_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("origin_published_at <= %s")
        params.append(date_to)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit = max(1, min(page_size, 100))
    offset = max(0, page) * limit

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM raw_news {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, title, news_url, processing_status, keyword, increased_items,
                       decreased_items, origin_published_at, retry_count, is_deleted
                FROM raw_news
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            return {"data": _rows(cur), "total": total}


@router.get("/analyses")
def list_analyses(
    page: int = 0,
    page_size: int = 50,
    search: str | None = None,
    min_reliability: float | None = None,
    time_horizon: str | None = None,
    geo_scope: str | None = None,
    korea_relevance: str | None = None,
):
    where = []
    params: list[object] = []
    if search:
        where.append("summary ILIKE %s")
        params.append(f"%{search}%")
    if min_reliability is not None:
        where.append("reliability >= %s")
        params.append(min_reliability)
    if time_horizon:
        where.append("time_horizon = %s")
        params.append(time_horizon)
    if geo_scope:
        where.append("geo_scope = %s")
        params.append(geo_scope)
    if korea_relevance:
        where.append("korea_relevance = %s")
        params.append(korea_relevance)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit = max(1, min(page_size, 100))
    offset = max(0, page) * limit
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM news_analyses {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, summary, reliability, time_horizon, geo_scope,
                       korea_relevance, created_at, effect_chain,
                       reliability_reason, raw_news_id
                FROM news_analyses
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            return {"data": _rows(cur), "total": total}
