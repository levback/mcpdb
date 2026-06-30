from __future__ import annotations

from typer.testing import CliRunner

from mcpdb.cli.app import app

runner = CliRunner()


def _assert_help(args: list[str], expected: str) -> None:
    result = runner.invoke(app, [*args, "--help"])
    assert result.exit_code == 0
    assert expected in result.stdout


def test_help_snapshots_match_golden() -> None:
    _assert_help([], "mcpdb command-line interface")
    _assert_help(["serve"], "--transport")
    _assert_help(["doctor"], "Usage")
    _assert_help(["config"], "Configuration commands")
    _assert_help(["audit"], "Audit commands")
    _assert_help(["audit", "verify"], "--key")
    _assert_help(["repl"], "Usage")
    _assert_help(["tools"], "Tool commands")
    _assert_help(["tools", "list"], "Usage")
    _assert_help(["profiles"], "Profile commands")
    _assert_help(["profiles", "list"], "Usage")
