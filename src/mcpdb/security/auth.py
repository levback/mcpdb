from __future__ import annotations

import hmac
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import jwt
from jwt import InvalidTokenError

SAFE_KID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class AuthError(ValueError):
    """Raised when bearer token validation fails."""


@dataclass(frozen=True)
class Principal:
    sub: str
    scopes: tuple[str, ...] = field(default_factory=tuple)
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JwtValidationSettings:
    issuer: str
    audience: str
    algorithms: tuple[str, ...]
    hs_secrets: dict[str, str] = field(default_factory=dict)
    public_keys: dict[str, str] = field(default_factory=dict)
    clock_skew_seconds: int = 60


def verify_authorization_header(header_value: str, settings: JwtValidationSettings) -> Principal:
    parts = header_value.strip().split(" ", maxsplit=1)
    if len(parts) != 2:
        raise AuthError("Authorization header must be in 'Bearer <token>' format")
    scheme, token = parts
    if not hmac.compare_digest(scheme.casefold(), "bearer"):
        raise AuthError("Authorization scheme must be Bearer")  # OWASP A07
    return verify_bearer(token, settings)


def verify_bearer(token: str, settings: JwtValidationSettings) -> Principal:
    try:
        unverified = jwt.get_unverified_header(token)
    except InvalidTokenError as error:
        raise AuthError("Malformed token header") from error

    algorithm = str(unverified.get("alg", ""))
    if algorithm.lower() == "none":
        raise AuthError("alg=none is rejected")  # OWASP A07
    if algorithm not in settings.algorithms:
        raise AuthError(f"Algorithm {algorithm} is not allowed")  # OWASP A07

    kid = str(unverified.get("kid", "default"))
    if not SAFE_KID_RE.fullmatch(kid):
        raise AuthError("Invalid token kid")  # OWASP A07

    key = _resolve_key(algorithm, kid, settings)

    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience=settings.audience,
            issuer=settings.issuer,
            leeway=settings.clock_skew_seconds,
            options={"require": ["sub", "exp", "iat", "nbf", "aud", "iss"]},
        )
    except InvalidTokenError as error:
        raise AuthError("Token validation failed") from error

    now_seconds = datetime.now(tz=UTC).timestamp()
    issued_at = float(claims["iat"])
    if issued_at > now_seconds + settings.clock_skew_seconds:
        raise AuthError("Token iat is too far in the future")

    subject = str(claims.get("sub", "")).strip()
    if not subject:
        raise AuthError("Token subject is required")

    return Principal(sub=subject, scopes=_parse_scopes(claims), claims=dict(claims))


def _resolve_key(algorithm: str, kid: str, settings: JwtValidationSettings) -> str:
    if algorithm.startswith("HS"):
        if kid not in settings.hs_secrets:
            raise AuthError(f"Unknown kid: {kid}")  # OWASP A07
        return settings.hs_secrets[kid]

    if kid not in settings.public_keys:
        raise AuthError(f"Unknown kid: {kid}")  # OWASP A07
    return settings.public_keys[kid]


def _parse_scopes(claims: dict[str, Any]) -> tuple[str, ...]:
    if isinstance(claims.get("scope"), str):
        return tuple(scope for scope in str(claims["scope"]).split() if scope)

    scopes_claim = claims.get("scopes")
    if isinstance(scopes_claim, list) and all(isinstance(scope, str) for scope in scopes_claim):
        return tuple(scope for scope in scopes_claim if scope)

    return ()
