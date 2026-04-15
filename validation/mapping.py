"""Category → indicator mapping.

Each entry: category_code → (table_name, value_column, date_key_column)

date_key_column:
  "reference_date"  → YYYY-MM-01 format  (ecos_monthly, kosis_monthly, gpr_monthly)
  "reference_month" → YYYY-MM format     (fred_monthly only)

shipping is intentionally omitted: fred_bdi is null across all rows.
"""
from __future__ import annotations

# (table_name, value_column, date_key_column)
CATEGORY_MAP: dict[str, tuple[str, str, str]] = {
    "oil":       ("indicator_ecos_monthly_logs",  "import_price_crude_oil",   "reference_date"),
    "fuel":      ("indicator_kosis_monthly_logs", "cpi_petroleum",            "reference_date"),
    "gas":       ("indicator_ecos_monthly_logs",  "import_price_natural_gas", "reference_date"),
    "energy":    ("indicator_ecos_monthly_logs",  "ppi_energy",               "reference_date"),
    "food":      ("indicator_ecos_monthly_logs",  "import_price_food",        "reference_date"),
    "wheat":     ("indicator_fred_monthly_logs",  "fred_wheat",               "reference_month"),
    "commodity": ("indicator_kosis_monthly_logs", "cpi_industrial",           "reference_date"),
    "price":     ("indicator_kosis_monthly_logs", "cpi_total",                "reference_date"),
    "inflation": ("indicator_fred_monthly_logs",  "fred_cpi",                 "reference_month"),
    "cost":      ("indicator_kosis_monthly_logs", "core_cpi",                 "reference_date"),
}

# Allowlists used by db.py to prevent SQL injection via identifier interpolation
_ALLOWED_TABLES: frozenset[str] = frozenset(t for t, _, _ in CATEGORY_MAP.values())
_ALLOWED_COLUMNS: frozenset[str] = frozenset(c for _, c, _ in CATEGORY_MAP.values()) | {
    "reference_date",
    "reference_month",
}
