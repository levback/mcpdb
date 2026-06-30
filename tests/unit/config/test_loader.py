import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcpdb.cli.config import app
from mcpdb.config.loader import ConfigLoadError, load_settings
from mcpdb.config.secrets import MemoryVault


def test_loader_env_var_precedence_over_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "mcpdb.yaml"
    config_path.write_text(
        """
limits:
  query_timeout_ms: 50
"""
    )
    monkeypatch.setenv("MCPDB__LIMITS__QUERY_TIMEOUT_MS", "250")

    settings = load_settings(config_path)

    assert settings.limits.query_timeout_ms == 250


def test_loader_unresolved_secret_ref_raises_with_path(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpdb.yaml"
    config_path.write_text(
        """
profiles:
  - name: main
    backend: postgres
    host: localhost
    database: app
    password: ${env:DOES_NOT_EXIST}
"""
    )

    with pytest.raises(ConfigLoadError, match=r"root.profiles\[0\]\.password"):
        load_settings(config_path)


def test_loader_yaml_duplicate_key_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpdb.yaml"
    config_path.write_text(
        """
limits:
  query_timeout_ms: 100
limits:
  query_timeout_ms: 200
"""
    )

    with pytest.raises(ConfigLoadError, match="Duplicate YAML key"):
        load_settings(config_path)


def test_loader_yaml_anchors_supported(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpdb.yaml"
    config_path.write_text(
        """
profiles:
  - &shared
    name: main
    backend: postgres
    host: localhost
    database: app
  - <<: *shared
    name: replica
"""
    )

    settings = load_settings(config_path)

    assert settings.profiles[0].host == "localhost"
    assert settings.profiles[1].database == "app"


def test_loader_file_not_found_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigLoadError, match="does not exist"):
        load_settings(tmp_path / "missing.yaml")


def test_loader_vault_ref_resolves_with_provider(tmp_path: Path) -> None:
    config_path = tmp_path / "mcpdb.yaml"
    config_path.write_text(
        """
profiles:
  - name: main
    backend: postgres
    host: localhost
    database: app
    password: ${vault:secret/db/password}
"""
    )

    settings = load_settings(
        config_path,
        vault_provider=MemoryVault({"secret/db/password": "topsecret"}),
    )

    assert settings.profiles[0].password is not None
    assert settings.profiles[0].password.get_secret_value() == "topsecret"


def test_cli_config_validate_succeeds(tmp_path: Path) -> None:
    config_path = tmp_path / "valid.yaml"
    config_path.write_text(
        """
profiles:
  - name: local
    backend: sqlite
    dsn: sqlite:///tmp/test.db
"""
    )

    runner = CliRunner()
    result = runner.invoke(app, ["config", "validate", str(config_path)])

    assert result.exit_code == 0
    assert "Config is valid" in result.stdout


def test_cli_config_validate_fails_for_invalid_file(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(
        """
profiles:
  - name: broken
    backend: sqlite
    mode: read_only
    allow_writes: true
    dsn: sqlite:///tmp/test.db
"""
    )

    runner = CliRunner()
    result = runner.invoke(app, ["config", "validate", str(config_path)])

    assert result.exit_code == 1
    assert "Invalid config" in result.stdout


def test_cli_config_schema_outputs_defs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["config", "schema"])

    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert "$defs" in payload
