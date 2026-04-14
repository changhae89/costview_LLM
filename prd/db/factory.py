"""Repository factory — returns the appropriate backend based on environment config."""

from __future__ import annotations

from prd.db.postgres_repository import PostgresRepository
from prd.db.supabase_client import create_sb, is_supabase_configured
from prd.db.supabase_repository import SupabaseRepository


def create_repository() -> PostgresRepository | SupabaseRepository:
    if is_supabase_configured():
        return SupabaseRepository(create_sb())

    from prd.db.connection import get_connection
    return PostgresRepository(get_connection())
