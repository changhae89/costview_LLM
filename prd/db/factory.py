"""Repository factory — returns the appropriate backend based on environment config."""

from __future__ import annotations

from prd.db.supabase_client import create_sb
from prd.db.supabase_repository import SupabaseRepository


def create_repository() -> SupabaseRepository:
    return SupabaseRepository(create_sb())
