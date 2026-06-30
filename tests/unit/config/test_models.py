import pytest
from pydantic import ValidationError

from mcpdb.config.models import Limits, McpDbSettings, Profile, Security


def test_models_defaults_match_deny_by_default() -> None:
    settings = McpDbSettings.model_validate({})

    assert settings.security.auth_enabled is False
    assert settings.security.bind_address == "127.0.0.1"
    assert settings.profiles == []


def test_profile_rejects_unknown_backend() -> None:
    with pytest.raises(ValidationError):
        Profile(name="main", backend="oracle", dsn="sqlite:///tmp.db")


def test_profile_requires_dsn_or_discrete_fields() -> None:
    with pytest.raises(ValidationError):
        Profile(name="main", backend="postgres")

    with pytest.raises(ValidationError):
        Profile(
            name="main",
            backend="postgres",
            dsn="postgresql://user:pass@localhost:5432/db",
            host="localhost",
            database="db",
        )

    valid = Profile(name="main", backend="postgres", host="localhost", database="db")
    assert valid.host == "localhost"


def test_security_rejects_bind_0_0_0_0_without_auth() -> None:
    with pytest.raises(ValidationError):
        Security(bind_address="0.0.0.0", auth_enabled=False)


def test_security_accepts_bind_127_0_0_1_without_auth() -> None:
    security = Security(bind_address="127.0.0.1", auth_enabled=False)

    assert security.bind_address == "127.0.0.1"


def test_limits_query_timeout_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Limits(query_timeout_ms=0)


def test_limits_max_rows_capped_at_one_million() -> None:
    with pytest.raises(ValidationError):
        Limits(max_rows=1_000_001)
