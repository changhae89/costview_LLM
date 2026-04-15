"""Category registry for PRD causal normalization."""

from __future__ import annotations

from functools import lru_cache

from prd.db.connection import get_connection
from prd.db.fetch import fetch_active_cost_categories

DEFAULT_ALLOWED_CATEGORIES = (
    "oil",
    "fuel",
    "gas",
    "energy",
    "food",
    "wheat",
    "commodity",
    "price",
    "cost",
    "inflation",
    "shipping",
)

CATEGORY_FALLBACK_MAP: dict[str, str] = {
    "원유": "oil",
    "유가": "oil",
    "배럴": "oil",
    "주유": "fuel",
    "휘발유": "fuel",
    "경유": "fuel",
    "연료": "fuel",
    "가스": "gas",
    "난방": "gas",
    "전기": "energy",
    "전력": "energy",
    "에너지": "energy",
    "장보기": "food",
    "마트": "food",
    "식료": "food",
    "외식": "food",
    "식당": "food",
    "밀": "wheat",
    "빵": "wheat",
    "곡물": "wheat",
    "농산물": "wheat",
    "원자재": "commodity",
    "국제": "commodity",
    "원료": "commodity",
    "물가": "price",
    "소비자가격": "price",
    "생활비": "cost",
    "가계": "cost",
    "대출": "cost",
    "금리": "cost",
    "이자": "cost",
    "인플레": "inflation",
    "물가상승": "inflation",
    "물류": "shipping",
    "배송": "shipping",
    "항공": "shipping",
    "해운": "shipping",
    "운송": "shipping",
}

LEGACY_ENGLISH_CATEGORY_MAP: dict[str, str] = {
    "utility": "energy",
    "utilities": "energy",
    "grocery": "food",
    "groceries": "food",
}


def _default_category_dicts() -> tuple[dict, ...]:
    return tuple({"code": c, "name_ko": c, "keywords": []} for c in DEFAULT_ALLOWED_CATEGORIES)


@lru_cache(maxsize=1)
def get_allowed_categories() -> tuple[dict, ...]:
    try:
        connection = get_connection()
    except Exception:
        return _default_category_dicts()

    try:
        categories = fetch_active_cost_categories(connection)
        return tuple(categories) if categories else _default_category_dicts()
    except Exception:
        return _default_category_dicts()
    finally:
        connection.close()


def build_english_fallback_map(categories: tuple[dict, ...] | None = None) -> dict[str, str]:
    """Build English fallback aliases from legacy mappings and DB keywords."""
    cats = categories if categories is not None else get_allowed_categories()
    result: dict[str, str] = dict(LEGACY_ENGLISH_CATEGORY_MAP)
    for cat in cats:
        for kw in (cat.get("keywords") or []):
            token = str(kw).strip().lower()
            if token:
                result[token] = cat["code"]
    return result
