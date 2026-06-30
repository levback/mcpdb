from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from mcpdb.cli.app import app
from mcpdb.config.models import McpDbSettings

runner = CliRunner()


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


def test_repl_handles_query_command(monkeypatch) -> None:
    async def fake_query(profile: str, statement: str, settings_obj):
        _ = (profile, statement, settings_obj)
        return {"row_count": 1, "rows": [{"value": 1}]}

    monkeypatch.setattr("mcpdb.cli.repl.load_settings", lambda _: _settings())
    monkeypatch.setattr("mcpdb.cli.repl._run_query", fake_query)

    result = runner.invoke(app, ["repl"], input="/query main SELECT 1\n/exit\n")

    assert result.exit_code == 0
    assert "row_count" in result.stdout


def test_repl_handles_unknown_command_gracefully(monkeypatch) -> None:
    monkeypatch.setattr("mcpdb.cli.repl.load_settings", lambda _: _settings())

    result = runner.invoke(app, ["repl"], input="/unknown\n/exit\n")

    assert result.exit_code == 0
    assert "unknown command" in result.stdout


def test_repl_help_profiles_and_tools(monkeypatch) -> None:
    monkeypatch.setattr("mcpdb.cli.repl.load_settings", lambda _: _settings())

    fake_defs = [SimpleNamespace(name="db.ping"), SimpleNamespace(name="db.query")]
    fake_service = SimpleNamespace(tool_definitions=lambda: fake_defs)
    monkeypatch.setattr(
        "mcpdb.cli.repl.build_server_components",
        lambda _settings: SimpleNamespace(tool_service=fake_service),
    )

    result = runner.invoke(app, ["repl"], input="/help\n/profiles\n/tools\n/exit\n")

    assert result.exit_code == 0
    assert "/help" in result.stdout
    assert "main:sqlite" in result.stdout
    assert "db.ping" in result.stdout


def test_repl_handles_ping_and_parse_errors(monkeypatch) -> None:
    async def fake_ping(profile: str, settings_obj):
        _ = (profile, settings_obj)
        return {"ok": True}

    monkeypatch.setattr("mcpdb.cli.repl.load_settings", lambda _: _settings())
    monkeypatch.setattr("mcpdb.cli.repl._run_ping", fake_ping)

    result = runner.invoke(app, ["repl"], input='/ping main\n"\n/exit\n')

    assert result.exit_code == 0
    assert "ok" in result.stdout
    assert "parse error" in result.stdout
