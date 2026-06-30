from __future__ import annotations

from typer.testing import CliRunner

from mcpdb.cli.app import app
from mcpdb.cli.doctor import DoctorResult
from mcpdb.config.loader import ConfigLoadError
from mcpdb.config.models import McpDbSettings

runner = CliRunner()


def _settings() -> McpDbSettings:
    return McpDbSettings.model_validate(
        {
            "profiles": [
                {
                    "name": "postgres_main",
                    "backend": "postgres",
                    "host": "localhost",
                    "database": "db",
                },
                {
                    "name": "mongo_main",
                    "backend": "mongodb",
                    "host": "localhost",
                    "database": "db",
                },
            ]
        }
    )


def test_doctor_reports_config_ok(monkeypatch) -> None:
    async def probe(name: str, profile: object) -> DoctorResult:
        _ = profile
        return DoctorResult(name=name, ok=True, detail="latency=1.00ms")

    monkeypatch.setattr("mcpdb.cli.doctor.load_settings", lambda _: _settings())
    monkeypatch.setattr("mcpdb.cli.doctor._probe_profile", probe)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_doctor_reports_secret_missing(monkeypatch) -> None:
    def fail_load(_path):
        raise ConfigLoadError("Unresolved SecretRef at root.profiles[0].password")

    monkeypatch.setattr("mcpdb.cli.doctor.load_settings", fail_load)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "FAIL config" in result.stdout


def test_doctor_reports_unreachable_postgres(monkeypatch) -> None:
    async def probe(name: str, profile: object) -> DoctorResult:
        _ = profile
        if name == "postgres_main":
            raise RuntimeError("postgres down")
        return DoctorResult(name=name, ok=True, detail="latency=1.00ms")

    monkeypatch.setattr("mcpdb.cli.doctor.load_settings", lambda _: _settings())
    monkeypatch.setattr("mcpdb.cli.doctor._probe_profile", probe)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "FAIL postgres_main" in result.stdout


def test_doctor_reports_unreachable_mongo(monkeypatch) -> None:
    async def probe(name: str, profile: object) -> DoctorResult:
        _ = profile
        if name == "mongo_main":
            raise RuntimeError("mongo down")
        return DoctorResult(name=name, ok=True, detail="latency=1.00ms")

    monkeypatch.setattr("mcpdb.cli.doctor.load_settings", lambda _: _settings())
    monkeypatch.setattr("mcpdb.cli.doctor._probe_profile", probe)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "FAIL mongo_main" in result.stdout


def test_doctor_exits_zero_on_all_green(monkeypatch) -> None:
    async def probe(name: str, profile: object) -> DoctorResult:
        _ = profile
        return DoctorResult(name=name, ok=True, detail="latency=1.00ms")

    monkeypatch.setattr("mcpdb.cli.doctor.load_settings", lambda _: _settings())
    monkeypatch.setattr("mcpdb.cli.doctor._probe_profile", probe)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
