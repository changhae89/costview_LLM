"""Supabase client initialization and utilities."""

from __future__ import annotations

import os


def is_supabase_configured() -> bool:
    """Check if Supabase environment variables are configured."""
    return bool(
        os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY")
    )


def create_sb():
    """Create and return a Supabase client.
    
    Raises:
        RuntimeError: If Supabase is not properly configured.
    """
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set"
        )

    return create_client(url, key)
