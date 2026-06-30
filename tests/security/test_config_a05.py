import pytest
from pydantic import ValidationError

from mcpdb.config.models import McpDbSettings


def test_security_dangerous_bind_default_rejected() -> None:
    with pytest.raises(ValidationError, match="requires auth_enabled=true"):
        McpDbSettings.model_validate(
            {
                "security": {"bind_address": "0.0.0.0", "auth_enabled": False},
                "profiles": [
                    {
                        "name": "main",
                        "backend": "sqlite",
                        "dsn": "sqlite:///tmp.db",
                    }
                ],
            }
        )


def test_security_read_only_cannot_allow_writes() -> None:
    with pytest.raises(ValidationError, match="allow_writes=true"):
        McpDbSettings.model_validate(
            {
                "profiles": [
                    {
                        "name": "main",
                        "backend": "sqlite",
                        "mode": "read_only",
                        "allow_writes": True,
                        "dsn": "sqlite:///tmp.db",
                    }
                ]
            }
        )
