from datetime import date

from fastapi import APIRouter

from db import get_conn

router = APIRouter()


def _rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@router.get("/today")
def get_today_briefing():
    today = date.today().isoformat()
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT id, briefing_date, headline, overview, items,
                           overall_risk, consumer_tip, indicators, source_count, created_at
                    FROM daily_briefings
                    WHERE briefing_date <= %s
                    ORDER BY briefing_date DESC
                    LIMIT 1
                    """,
                    [today],
                )
                rows = _rows(cur)
            except Exception:
                return {"data": None}
    return {"data": rows[0] if rows else None}


@router.get("/history")
def get_briefing_history(days: int = 7):
    days = max(1, min(days, 30))
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT id, briefing_date, headline, overall_risk, source_count, created_at
                    FROM daily_briefings
                    ORDER BY briefing_date DESC
                    LIMIT %s
                    """,
                    [days],
                )
                rows = _rows(cur)
            except Exception:
                return {"data": []}
    return {"data": rows}
