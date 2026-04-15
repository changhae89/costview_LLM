import pytest

from prd.db import supabase_client


def test_is_supabase_configured_false_without_env(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    assert supabase_client.is_supabase_configured() is False


def test_create_sb_requires_installed_package_when_supabase_env_present(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(supabase_client, "create_client", None)

    with pytest.raises(RuntimeError, match="package is not installed"):
        supabase_client.create_sb()
