"""Category → indicator mapping.

Each entry: category_code → (table_name, value_column, date_key_column)

date_key_column:
  "reference_date"  → YYYY-MM-01 format  (ecos_monthly, kosis_monthly, gpr_monthly)
  "reference_month" → YYYY-MM format     (fred_monthly only)
  "reference_date"  → daily tables also use this key, but fetched via monthly avg aggregation

geo_scope routing:
  korea / asia → CATEGORY_MAP_KOREA  (KOSIS/ECOS)
  global / others → CATEGORY_MAP_GLOBAL (FRED)

shipping is intentionally omitted: fred_bdi is null across all rows.
"""
from __future__ import annotations

# (table_name, value_column, date_key_column)

# Korea/Asia geo_scope → KOSIS/ECOS
CATEGORY_MAP_KOREA: dict[str, tuple[str, str, str]] = {
    "oil":       ("indicator_ecos_monthly_logs",  "import_price_crude_oil",   "reference_date"),
    "fuel":      ("indicator_ecos_monthly_logs",  "import_price_crude_oil",   "reference_date"),
    "gas":       ("indicator_ecos_monthly_logs",  "import_price_natural_gas", "reference_date"),
    "energy":    ("indicator_ecos_monthly_logs",  "ppi_energy",               "reference_date"),
    "food":      ("indicator_ecos_monthly_logs",  "import_price_food",        "reference_date"),
    "wheat":     ("indicator_fred_monthly_logs",  "fred_wheat",               "reference_month"),
    "commodity": ("indicator_fred_monthly_logs",  "fred_corn",                "reference_month"),
    "price":     ("indicator_kosis_monthly_logs", "cpi_total",                "reference_date"),
    "inflation": ("indicator_fred_monthly_logs",  "fred_cpi",                 "reference_month"),
    "cost":      ("indicator_kosis_monthly_logs", "core_cpi",                 "reference_date"),
}

# Global geo_scope → FRED
CATEGORY_MAP_GLOBAL: dict[str, tuple[str, str, str]] = {
    "oil":       ("indicator_fred_daily_logs",    "fred_wti",          "reference_date"),
    "fuel":      ("indicator_fred_monthly_logs",  "fred_ppi",          "reference_month"),
    "gas":       ("indicator_fred_daily_logs",    "fred_natural_gas",  "reference_date"),
    "energy":    ("indicator_fred_daily_logs",    "fred_heating_oil",  "reference_date"),
    "food":      ("indicator_fred_monthly_logs",  "fred_corn",         "reference_month"),
    "wheat":     ("indicator_fred_monthly_logs",  "fred_wheat",        "reference_month"),
    "commodity": ("indicator_fred_monthly_logs",  "fred_corn",         "reference_month"),
    "price":     ("indicator_fred_monthly_logs",  "fred_cpi",          "reference_month"),
    "inflation": ("indicator_fred_monthly_logs",  "fred_cpi",          "reference_month"),
    "cost":      ("indicator_fred_monthly_logs",  "fred_ppi",          "reference_month"),
}

# Backwards compat alias
CATEGORY_MAP = CATEGORY_MAP_KOREA

# Daily tables: need monthly average aggregation instead of direct key lookup
_DAILY_TABLES: frozenset[str] = frozenset({"indicator_fred_daily_logs"})

# Geo scopes routed to KOREA mapping; everything else uses GLOBAL
_KOREA_GEO_SCOPES: frozenset[str] = frozenset({"korea", "asia"})


def get_category_mapping(category: str, geo_scope: str | None) -> tuple[str, str, str] | None:
    """Return (table, value_col, date_key_col) based on category and geo_scope."""
    scope = (geo_scope or "global").lower()
    cat_map = CATEGORY_MAP_KOREA if scope in _KOREA_GEO_SCOPES else CATEGORY_MAP_GLOBAL
    return cat_map.get(category)


# 카테고리별 키워드 (cost_categories.keywords 기반, 후속 뉴스 매칭용)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "oil":       ["oil", "crude", "petroleum", "opec", "barrel"],
    "fuel":      ["fuel", "gasoline", "petrol", "diesel"],
    "gas":       ["gas", "natural gas", "lng", "lpg"],
    "energy":    ["energy", "electricity", "power", "utility"],
    "food":      ["food", "grocery", "meat", "dairy", "produce"],
    "wheat":     ["wheat", "grain", "corn", "rice", "soybean"],
    "commodity": ["commodity", "raw material", "iron", "steel", "cotton"],
    "price":     ["price", "consumer price", "cpi"],
    "inflation": ["inflation", "deflation", "stagflation"],
    "cost":      ["cost", "living cost", "expense", "wage"],
    "shipping":  ["shipping", "freight", "logistics", "supply chain", "port"],
}

# Allowlists used by db.py to prevent SQL injection via identifier interpolation
_all_maps = list(CATEGORY_MAP_KOREA.values()) + list(CATEGORY_MAP_GLOBAL.values())
_ALLOWED_TABLES: frozenset[str] = frozenset(t for t, _, _ in _all_maps)
_ALLOWED_COLUMNS: frozenset[str] = frozenset(c for _, c, _ in _all_maps) | {
    "reference_date",
    "reference_month",
}
