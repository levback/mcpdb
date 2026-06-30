from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcpdb.security.secrets import EnvVault, FileVault, SecuritySecretError
from mcpdb.server.errors import map_exception


def test_security_owasp_a02_secret_not_in_500_body() -> None:
    mapped = map_exception(RuntimeError("postgresql://admin:super-secret@db.local/prod"))

    assert "super-secret" not in mapped.message


def test_security_owasp_a02_file_vault_permission_guard(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    path.write_text('{"db/password":"secret"}', encoding="utf-8")
    os.chmod(path, 0o644)

    vault = FileVault(path)
    with pytest.raises(SecuritySecretError, match="0600"):
        vault.resolve("db/password")


def test_security_owasp_a02_file_vault_requires_owner_rw(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    path.write_text('{"db/password":"secret"}', encoding="utf-8")
    os.chmod(path, 0o000)

    vault = FileVault(path)
    with pytest.raises(SecuritySecretError, match="owner read/write"):
        vault.resolve("db/password")


def test_security_owasp_a02_env_vault_missing_secret_has_safe_message() -> None:
    vault = EnvVault(prefix="MCPDB_")

    with pytest.raises(SecuritySecretError) as raised:
        vault.resolve("MISSING_SECRET")

    assert "super-secret" not in str(raised.value)
