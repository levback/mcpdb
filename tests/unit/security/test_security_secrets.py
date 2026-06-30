from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcpdb.security.secrets import AwsSmVault, EnvVault, FileVault, SecuritySecretError


def test_env_vault_reads_prefixed_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCPDB_DB_PASSWORD", "topsecret")

    vault = EnvVault(prefix="MCPDB_")

    assert vault.resolve("DB_PASSWORD") == "topsecret"


def test_file_vault_reads_value_with_0600_permissions(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    path.write_text('{"db/password":"secret"}', encoding="utf-8")
    os.chmod(path, 0o600)

    vault = FileVault(path)

    assert vault.resolve("db/password") == "secret"


def test_file_vault_rejects_missing_owner_rw_permissions(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    path.write_text('{"db/password":"secret"}', encoding="utf-8")
    os.chmod(path, 0o400)

    vault = FileVault(path)

    with pytest.raises(SecuritySecretError, match="owner read/write"):
        vault.resolve("db/password")


def test_aws_sm_vault_is_explicit_stub() -> None:
    vault = AwsSmVault(region="eu-west-1")

    with pytest.raises(NotImplementedError, match="stub"):
        vault.resolve("db/password")
