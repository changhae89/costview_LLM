"""Collect economic indicator snapshots."""

from __future__ import annotations

import httpx

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CostView/1.0)"}

BASE_RATE = 3.50

TICKERS = [
    ("USDKRW=X", "usd_krw", "KRW", "원/달러 환율"),
    ("CL=F", "wti", "USD", "WTI 유가"),
    ("GC=F", "gold", "USD", "금 가격"),
]


async def fetch_all_indicators() -> list[dict[str, object]]:
    """Collect public market indicators plus the maintained base rate constant."""
    results: list[dict[str, object]] = []

    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        for ticker, indicator_type, unit, label in TICKERS:
            try:
                data = await _fetch_yahoo(client, ticker, indicator_type, unit)
                results.append(data)
                print(f"[indicator] OK {label}: {data['value']} {unit}")
            except Exception as error:
                print(f"[indicator] FAIL {label} 수집 실패: {error}")

    results.append(
        {
            "type": "base_rate",
            "value": BASE_RATE,
            "unit": "%",
            "source": "한국은행 (코드 관리)",
        }
    )
    print(f"[indicator] OK 기준금리: {BASE_RATE}%")
    return results


async def _fetch_yahoo(
    client: httpx.AsyncClient,
    ticker: str,
    indicator_type: str,
    unit: str,
) -> dict[str, object]:
    """Fetch the latest market price for a Yahoo Finance ticker."""
    response = await client.get(f"{YAHOO_BASE}/{ticker}")
    response.raise_for_status()

    data = response.json()
    meta = data["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]

    return {
        "type": indicator_type,
        "value": round(float(price), 4),
        "unit": unit,
        "source": "Yahoo Finance",
    }
