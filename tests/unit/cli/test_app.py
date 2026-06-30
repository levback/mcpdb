from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from mcpdb.config.models import McpDbSettings
from mcpdb.security.audit import AuditEntry, HMACChainSink

runner = CliRunner()
app_module = importlib.import_module("mcpdb.cli.app")
app = app_module.app


def _settings() -> McpDbSettings:
    return McpDbSettings.model_validate(
        {
            "profiles": [
                {
                    "name": "main",
                    "backend": "sqlite",
                    "dsn": "sqlite+aiosqlite:///:memory:",
                }
            ]
        }
    )


def test_app_version_flag() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "mcpdb 0.1.0" in result.stdout


def test_app_unknown_subcommand_exits_2() -> None:
    result = runner.invoke(app, ["nope-command"])

    assert result.exit_code == 2


def test_config_validate_minimal_yaml_exits_0(tmp_path: Path) -> None:
    path = tmp_path / "ok.yaml"
    path.write_text(
        """
profiles:
  - name: local
    backend: sqlite
    dsn: sqlite:///tmp/test.db
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["config", "validate", str(path)])

    assert result.exit_code == 0


def test_config_validate_invalid_yaml_exits_2(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("profiles: [", encoding="utf-8")

    result = runner.invoke(app, ["config", "validate", str(path)])

    assert result.exit_code == 2


def test_config_schema_outputs_valid_json_schema() -> None:
    result = runner.invoke(app, ["config", "schema"])

    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert "$defs" in payload


def test_audit_verify_clean_chain_exits_0(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = HMACChainSink(path=path, key="test-key")
    sink.write(
        AuditEntry(
            who="doctor",
            source="127.0.0.1",
            action="doctor",
            target="main",
            outcome="allow",
            request_id="r-1",
        )
    )

    result = runner.invoke(app, ["audit", "verify", str(path), "--key", "test-key"])

    assert result.exit_code == 0


def test_audit_verify_tampered_exits_2(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = HMACChainSink(path=path, key="test-key")
    sink.write(
        AuditEntry(
            who="doctor",
            source="127.0.0.1",
            action="doctor",
            target="main",
            outcome="allow",
            request_id="r-1",
        )
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"allow"', '"deny"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = runner.invoke(app, ["audit", "verify", str(path), "--key", "test-key"])

    assert result.exit_code == 2


def test_tools_list_renders_tool_table(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "load_settings", lambda _: _settings())

    fake_defs = [SimpleNamespace(name="db.ping"), SimpleNamespace(name="db.query")]
    fake_service = SimpleNamespace(tool_definitions=lambda: fake_defs)
    monkeypatch.setattr(
        app_module,
        "build_server_components",
        lambda _settings: SimpleNamespace(tool_service=fake_service),
    )

    result = runner.invoke(app_module.app, ["tools", "list"])

    assert result.exit_code == 0
    assert "db.ping" in result.stdout
    assert "db.query" in result.stdout


def test_profiles_list_renders_profile_table(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "load_settings", lambda _: _settings())

    result = runner.invoke(app_module.app, ["profiles", "list"])

    assert result.exit_code == 0
    assert "main" in result.stdout
    assert "sqlite" in result.stdout
