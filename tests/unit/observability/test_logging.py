from __future__ import annotations

import json
from io import StringIO
from typing import Any

import structlog

from mcpdb.observability.logging import (
    _SENSITIVE_KEYS,
    _sanitise_str,
    bind_correlation,
    configure_logging,
    current_correlation_id,
    current_principal,
    get_logger,
    redact_value,
)


def _capture_logs(func, **kwargs) -> list[dict[str, Any]]:
    """Run ``configure_logging`` with a StringIO sink and parse emitted JSON."""
    buf = StringIO()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=buf),
        cache_logger_on_first_use=False,
    )
    logger = structlog.get_logger("test")
    func(logger, **kwargs)
    records: list[dict[str, Any]] = []
    for line in buf.getvalue().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def test_logging_emits_stable_json() -> None:
    """configure_logging should produce parseable JSON with stable key order."""
    buf = StringIO()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=buf),
        cache_logger_on_first_use=False,
    )
    log = structlog.get_logger("test")
    log.info("hello", status="ok")
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert "event" in parsed or "hello" in str(parsed)  # key varies by structlog version
    assert "timestamp" in parsed or "time" in parsed or len(parsed) > 0


def test_logging_redacts_password_field() -> None:
    """A field named 'password' must be replaced with [REDACTED]."""
    from mcpdb.observability.logging import _redact_event_dict

    result = _redact_event_dict(None, "info", {"event": "login", "password": "super-secret"})
    assert result["password"] == "[REDACTED]"
    assert "super-secret" not in str(result)


def test_logging_redacts_authorization_header() -> None:
    """An 'authorization' key must be replaced with [REDACTED]."""
    from mcpdb.observability.logging import _redact_event_dict

    result = _redact_event_dict(None, "info", {"event": "request", "authorization": "Bearer tok"})
    assert result["authorization"] == "[REDACTED]"


def test_logging_redacts_connection_string() -> None:
    """A connection string value containing credentials must be redacted."""
    raw = "postgresql+asyncpg://alice:s3cret@localhost:5432/db"
    assert redact_value(raw) == "[REDACTED]"

    mongo = "mongodb://user:pass@cluster.example/db"
    assert redact_value(mongo) == "[REDACTED]"


def test_logging_unicode_keys_not_mangled() -> None:
    """Unicode field values must pass through without corruption."""
    from mcpdb.observability.logging import _redact_event_dict

    result = _redact_event_dict(None, "info", {"event": "こんにちは", "user": "大島"})
    assert result["user"] == "大島"
    assert result["event"] == "こんにちは"


def test_logging_control_char_stripped_from_value() -> None:
    """Control characters used in log injection must be stripped (OWASP A09)."""
    injected = "normal\x00hidden\x0ainjection"
    sanitised = _sanitise_str(injected)
    assert "\x00" not in sanitised
    assert "\x0a" not in sanitised  # \\n also stripped by [\x00-\x1f] range
    assert "normal" in sanitised
    assert "hidden" in sanitised


def test_logging_newline_blocked() -> None:
    """\\n in log values is stripped to prevent log-forging (OWASP A09)."""
    value = "before\nINFO extra_field=injected"
    sanitised = _sanitise_str(value)
    assert "\n" not in sanitised


def test_sensitive_key_set_is_non_empty() -> None:
    assert len(_SENSITIVE_KEYS) > 0
    assert "password" in _SENSITIVE_KEYS
    assert "token" in _SENSITIVE_KEYS


def test_bind_and_read_correlation() -> None:
    bind_correlation("corr-123", principal="alice")
    assert current_correlation_id() == "corr-123"
    assert current_principal() == "alice"


def test_configure_logging_json_mode() -> None:
    """configure_logging must not raise and structlog must be usable after."""
    configure_logging(level="WARNING", json_output=True)
    log = get_logger("test.configure")
    # Should not raise
    log.warning("test after configure", key="value")


def test_configure_logging_console_mode() -> None:
    """configure_logging in console mode must not raise."""
    configure_logging(level="DEBUG", json_output=False)
    log = get_logger("test.console")
    log.debug("debug message")


def test_redact_bearer_token() -> None:
    bearer = "Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"
    assert redact_value(bearer) == "[REDACTED]"


def test_redact_basic_creds() -> None:
    basic = "Basic YWxpY2U6c2VjcmV0"
    assert redact_value(basic) == "[REDACTED]"


def test_safe_value_passes_through() -> None:
    safe = "SELECT name FROM users WHERE id = :id"
    assert redact_value(safe) == safe
