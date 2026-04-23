from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_auth
from db import get_conn

router = APIRouter(dependencies=[Depends(require_auth)])

IndicatorGroup = Literal["gpr", "ecos", "fred", "kosis"]

INDICATORS: dict[str, tuple[str, list[str]]] = {
    "gpr": (
        "indicator_gpr_daily_logs",
        ["reference_date", "ai_gpr_index", "gpr_original", "oil_disruptions", "non_oil_gpr"],
    ),
    "ecos": (
        "indicator_ecos_daily_logs",
        ["reference_date", "krw_usd_rate"],
    ),
    "fred": (
        "indicator_fred_daily_logs",
        [
            "reference_date",
            "fred_wti",
            "fred_brent",
            "fred_natural_gas",
            "fred_treasury_10y",
            "fred_treasury_2y",
            "fred_usd_index",
        ],
    ),
    "kosis": (
        "indicator_kosis_monthly_logs",
        ["reference_date", "cpi_total", "core_cpi", "cpi_petroleum", "cpi_agro"],
    ),
}


@router.get("/{group}")
def get_indicator_series(group: IndicatorGroup, days: int | None = Query(default=None, ge=1, le=5000)):
    table, columns = INDICATORS.get(group, (None, None))
    if table is None or columns is None:
        raise HTTPException(status_code=404, detail="indicator_not_found")

    where = ""
    params: tuple[int, ...] = ()
    if days is not None:
        where = "WHERE reference_date::date >= CURRENT_DATE - (%s::int * INTERVAL '1 day')"
        params = (days,)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {', '.join(columns)}
                FROM {table}
                {where}
                ORDER BY reference_date ASC
                LIMIT 2000
                """,
                params,
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
