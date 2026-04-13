"""Postgres connection helpers for PRD analysis."""

from __future__ import annotations

import psycopg2 as psycopg

from prd.common.supabase_client import is_supabase_configured
from prd.config import get_database_url


def get_connection():
    """Create a transactional Postgres connection for PRD analysis."""
    if is_supabase_configured():
        raise RuntimeError(
            "SUPABASE_URL and a Supabase key are configured. Use prd.common.supabase_client instead."
        )

    database_url = get_database_url()
    if not database_url:
        raise RuntimeError(
            "Set DATABASE_URL or POSTGRES_URL, or configure SUPABASE_URL with a Supabase key."
        )

    if "sslmode" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    connection = psycopg.connect(database_url)
    connection.autocommit = False
    return connection

