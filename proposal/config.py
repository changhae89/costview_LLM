"""Environment loading and configuration helpers for the proposal package."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


def load_environment() -> None:
    """Load repo-level defaults first, then let proposal-specific values override them."""
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(PACKAGE_DIR / ".env", override=True)


def get_database_url() -> str:
    """Return the configured Postgres connection URL."""
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if database_url:
        return database_url

    legacy_api_key = os.environ.get("API_KEY", "")
    if legacy_api_key.startswith("postgresql://") or legacy_api_key.startswith("postgres://"):
        return legacy_api_key

    return ""


def get_supabase_url() -> str:
    """Return the configured Supabase project URL."""
    return os.environ.get("SUPABASE_URL", "").strip()


def get_supabase_key() -> str:
    """Return the best available Supabase API key for server-side access."""
    for key_name in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_KEY"):
        value = os.environ.get(key_name, "").strip()
        if value:
            return value
    return ""

