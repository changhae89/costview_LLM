"""Supabase client helpers used by the proposal package."""

from __future__ import annotations

from supabase import Client, create_client

from proposal.config import get_supabase_key, get_supabase_url


def is_supabase_configured() -> bool:
    """Return whether the minimum Supabase configuration is present."""
    return bool(get_supabase_url() and get_supabase_key())


def create_sb() -> Client:
    """Create and return a Supabase client."""
    supabase_url = get_supabase_url()
    supabase_key = get_supabase_key()

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and one of SUPABASE_SERVICE_ROLE_KEY/SUPABASE_ANON_KEY/SUPABASE_KEY are required."
        )

    return create_client(supabase_url, supabase_key)
