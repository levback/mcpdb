from __future__ import annotations

from pydantic import ValidationError


def validate_profile_constraints(mode: str, allow_writes: bool, profile_name: str) -> None:
    if mode == "read_only" and allow_writes:
        raise ValueError(
            f"Profile '{profile_name}' cannot set allow_writes=true in read_only mode"  # OWASP A05
        )


def validate_security_constraints(bind_address: str, auth_enabled: bool) -> None:
    if bind_address == "0.0.0.0" and not auth_enabled:
        raise ValueError(
            "bind_address=0.0.0.0 requires auth_enabled=true"  # OWASP A05
        )


def validate_limits_constraints(query_timeout_ms: int, max_rows: int) -> None:
    if query_timeout_ms < 1:
        raise ValueError("query_timeout_ms must be >= 1")
    if max_rows > 1_000_000:
        raise ValueError("max_rows must be <= 1_000_000")


def format_validation_error(error: ValidationError) -> str:
    pieces: list[str] = []
    for item in error.errors(include_url=False):
        location = ".".join(str(part) for part in item["loc"])
        pieces.append(f"{location}: {item['msg']}")
    return "\n".join(pieces)
