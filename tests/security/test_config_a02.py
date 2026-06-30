import logging

import pytest

from mcpdb.config.models import McpDbSettings
from mcpdb.config.secrets import MemoryVault


def _build_settings() -> McpDbSettings:
    return McpDbSettings.model_validate(
        {
            "profiles": [
                {
                    "name": "main",
                    "backend": "postgres",
                    "host": "localhost",
                    "database": "app",
                    "password": "super-secret",
                }
            ]
        }
    )


def test_security_repr_never_contains_password_keyword() -> None:
    rendered = repr(_build_settings())

    assert "super-secret" not in rendered
    assert "**********" in rendered


def test_security_logging_does_not_leak_secret_value(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    vault = MemoryVault({"secret/db": "super-secret"})

    vault.resolve("secret/db")

    assert "super-secret" not in caplog.text


def test_security_schema_export_has_no_secrets() -> None:
    schema = McpDbSettings.model_json_schema()
    serialized = str(schema)

    assert "super-secret" not in serialized
    assert "password" in serialized
