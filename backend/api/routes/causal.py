from fastapi import APIRouter, Depends

from auth import require_auth
from db import get_conn

router = APIRouter(dependencies=[Depends(require_auth)])


def _rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@router.get("/")
def list_causal_chains(
    page: int = 0,
    page_size: int = 50,
    category: str | None = None,
    direction: str | None = None,
    magnitude: str | None = None,
    transmission_months: int | None = None,
):
    where = []
    params: list[object] = []
    if category:
        where.append("cc.category = %s")
        params.append(category)
    if direction:
        where.append("cc.direction = %s")
        params.append(direction)
    if magnitude:
        where.append("cc.magnitude = %s")
        params.append(magnitude)
    if transmission_months:
        where.append("cc.transmission_time_months = %s")
        params.append(transmission_months)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit = max(1, min(page_size, 100))
    offset = max(0, page) * limit

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM causal_chains cc {where_sql}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT
                  cc.id, cc.event, cc.category, cc.direction, cc.magnitude,
                  cc.raw_shock_percent, cc.wallet_hit_percent, cc.transmission_time_months,
                  cc.mechanism, cc.logic_steps, cc.raw_shock_factors,
                  cc.wallet_hit_factors, cc.transmission_rationale,
                  json_build_object(
                    'id', na.id,
                    'reliability', na.reliability,
                    'created_at', na.created_at,
                    'summary', na.summary
                  ) AS news_analyses
                FROM causal_chains cc
                INNER JOIN news_analyses na ON na.id = cc.news_analysis_id
                {where_sql}
                ORDER BY cc.id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            return {"data": _rows(cur), "total": total}


@router.get("/stats")
def get_causal_stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category, direction, magnitude, raw_shock_percent,
                       wallet_hit_percent, transmission_time_months
                FROM causal_chains
                """
            )
            return _rows(cur)
