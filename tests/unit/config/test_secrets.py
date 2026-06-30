import logging

import pytest

from mcpdb.config.secrets import EnvProvider, MemoryVault, SecretResolutionError


def test_secrets_env_provider_resolves_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PG_PASSWORD", "secret-value")

    provider = EnvProvider()

    assert provider.resolve("pg_password") == "secret-value"


def test_secrets_memory_vault_returns_value_once_then_redacts_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    vault = MemoryVault({"secret/db": "very-secret"})

    value = vault.resolve("secret/db")
    second_value = vault.resolve("secret/db")

    assert value == "very-secret"
    assert second_value == "[REDACTED]"
    assert "very-secret" not in caplog.text


def test_secrets_missing_env_raises_with_required_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_ENV", raising=False)

    provider = EnvProvider()

    with pytest.raises(SecretResolutionError, match="MISSING_ENV"):
        provider.resolve("MISSING_ENV")


def test_secrets_memory_vault_missing_key_raises() -> None:
    vault = MemoryVault({})

    with pytest.raises(SecretResolutionError, match="Vault key is missing"):
        vault.resolve("secret/missing")
