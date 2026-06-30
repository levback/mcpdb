from __future__ import annotations

import contextvars
import logging as _stdlib_logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

# Correlation ID propagated across async boundaries via contextvars — NIST AU-3
_CORRELATION_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="unknown"
)
_PRINCIPAL: contextvars.ContextVar[str] = contextvars.ContextVar("principal", default="anonymous")

# ──────────────────────────────────────────────────────────────────────────────
# Secret redaction — OWASP A09
# ──────────────────────────────────────────────────────────────────────────────

_REDACTED = "[REDACTED]"

# Field names that must always be redacted regardless of value
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "auth",
        "api_key",
        "apikey",
        "dsn",
        "connection_string",
        "private_key",
        "access_key",
        "secret_key",
    }
)

# Regex patterns applied to string VALUES — catches connection strings / bearer headers
_SENSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"postgresql(?:\+[^:]+)?://[^@]+@", re.IGNORECASE),  # PG DSN with creds
    re.compile(r"mysql(?:\+[^:]+)?://[^@]+@", re.IGNORECASE),  # MySQL DSN with creds
    re.compile(r"mongodb(?:\+srv)?://[^@]+@", re.IGNORECASE),  # Mongo DSN with creds
    re.compile(r"bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),  # Bearer token
    re.compile(r"Basic\s+[A-Za-z0-9+/=]+", re.IGNORECASE),  # HTTP Basic creds
)

# Control characters that would allow log-forging — NIST SI-10 / OWASP A09
# Includes \n (0x0a), \r (0x0d) explicitly to block log injection.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def redact_value(value: str) -> str:
    """Replace credential patterns in a string with the redaction placeholder."""
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(value):
            return _REDACTED
    return value


def _sanitise_str(value: str) -> str:
    """Strip control chars (log injection) then check credential patterns."""
    cleaned = _CONTROL_CHAR_RE.sub("", value)  # OWASP A09: remove log-forging chars
    return redact_value(cleaned)


def _redact_event_dict(
    logger: Any, method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: redact sensitive keys and sanitise string values."""
    safe: MutableMapping[str, Any] = {}
    for key, value in event_dict.items():
        lower_key = key.lower()
        if lower_key in _SENSITIVE_KEYS:
            safe[key] = _REDACTED  # OWASP A09: never log secret fields
        elif isinstance(value, str):
            safe[key] = _sanitise_str(value)
        else:
            safe[key] = value
    return safe


def _inject_correlation(
    logger: Any, method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: inject correlation_id and principal from context."""
    event_dict.setdefault("correlation_id", _CORRELATION_ID.get())
    event_dict.setdefault("principal", _PRINCIPAL.get())
    return event_dict


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def configure_logging(*, level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog for JSON-first, redacted, UTC-timestamped output.

    Call once at process startup. Repeated calls reconfigure logger behavior.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO-8601 UTC — §5.1
        _inject_correlation,
        _redact_event_dict,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        final_renderer: structlog.types.Processor = structlog.processors.JSONRenderer(
            sort_keys=True  # stable key order — §5.1
        )
    else:
        final_renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, final_renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            _stdlib_logging.getLevelName(level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Keep stdlib logging output aligned with structlog renderers.
    _stdlib_logging.basicConfig(level=level.upper(), stream=sys.stdout, format="%(message)s")


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a module-scoped structlog logger."""
    bound: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return bound


def bind_correlation(correlation_id: str, principal: str = "anonymous") -> None:
    """Store correlation_id and principal into the current async context."""
    _CORRELATION_ID.set(correlation_id)
    _PRINCIPAL.set(principal)


def current_correlation_id() -> str:
    return _CORRELATION_ID.get()


def current_principal() -> str:
    return _PRINCIPAL.get()
