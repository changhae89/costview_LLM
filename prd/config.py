"""Environment loading and configuration helpers for the PRD package."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


def load_environment() -> None:
    """Load repo defaults first, then let PRD-specific values override them."""
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


def get_gemini_api_key() -> str:
    """Return the configured Gemini API key."""
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()


def get_gemini_model() -> str:
    """Return the configured Gemini model id (main model for full analysis)."""
    return (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash-lite").strip()


def get_gemini_flash_model() -> str:
    """Return the flash model id used for lightweight pre-classify calls."""
    return (os.environ.get("GEMINI_FLASH_MODEL") or "gemini-2.5-flash-lite").strip()



def get_max_batch() -> int:
    """Return the configured PRD batch size."""
    raw = (os.environ.get("PRD_MAX_BATCH") or "100").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def get_concurrency() -> int:
    """Return the configured PRD concurrency (number of news processed in parallel)."""
    raw = (os.environ.get("PRD_CONCURRENCY") or "1").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1
