from __future__ import annotations

from typer.testing import CliRunner

from mcpdb.cli.app import app
from mcpdb.config.models import McpDbSettings

runner = CliRunner()


def _settings(auth_enabled: bool) -> McpDbSettings:
    return McpDbSettings.model_validate(
        {
            "profiles": [
                {
                    "name": "main",
                    "backend": "sqlite",
                    "dsn": "sqlite+aiosqlite:///:memory:",
                }
            ],
            "security": {"auth_enabled": auth_enabled},
        }
    )


def test_serve_overrides_bind_from_cli(monkeypatch) -> None:
    called: dict[str, object] = {}

    monkeypatch.setattr("mcpdb.cli.serve.load_settings", lambda _: _settings(auth_enabled=True))

    def fake_run(app_obj, host: str, port: int, log_level: str) -> None:
        called.update({"host": host, "port": port, "log_level": log_level})

    monkeypatch.setattr("mcpdb.cli.serve.uvicorn.run", fake_run)

    result = runner.invoke(
        app,
        ["serve", "--transport", "http", "--bind", "127.0.0.1", "--port", "8765"],
    )

    assert result.exit_code == 0
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 8765


def test_serve_rejects_non_loopback_without_auth(monkeypatch) -> None:
    monkeypatch.setattr("mcpdb.cli.serve.load_settings", lambda _: _settings(auth_enabled=False))

    result = runner.invoke(app, ["serve", "--bind", "0.0.0.0"])

    assert result.exit_code == 2
    assert "non-loopback" in (result.stdout + result.stderr)


def test_serve_stdio_invokes_anyio_runner(monkeypatch) -> None:
    called: dict[str, object] = {}

    monkeypatch.setattr("mcpdb.cli.serve.load_settings", lambda _: _settings(auth_enabled=True))

    fake_server = type(
        "FakeServer",
        (),
        {
            "run": lambda self, read_stream, write_stream, init_options: None,
            "create_initialization_options": lambda self: {},
        },
    )()
    monkeypatch.setattr("mcpdb.cli.serve.build_server", lambda _settings: fake_server)

    def fake_anyio_run(func) -> None:
        called["name"] = getattr(func, "__name__", "")

    monkeypatch.setattr("mcpdb.cli.serve.anyio.run", fake_anyio_run)

    result = runner.invoke(app, ["serve", "--transport", "stdio"])

    assert result.exit_code == 0
    assert called["name"] == "_serve_stdio"
