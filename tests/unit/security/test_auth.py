from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from mcpdb.security.auth import (
    AuthError,
    JwtValidationSettings,
    verify_authorization_header,
    verify_bearer,
)

TEST_HS_KEY = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def hs_settings() -> JwtValidationSettings:
    return JwtValidationSettings(
        issuer="https://issuer.example",
        audience="mcpdb-client",
        algorithms=("HS256",),
        hs_secrets={"default": TEST_HS_KEY},
    )


def _mint_hs_token(
    *,
    secret: str,
    issuer: str,
    audience: str,
    subject: str = "user-1",
    expires_delta: timedelta = timedelta(minutes=5),
    not_before_delta: timedelta = timedelta(seconds=0),
    issued_at_delta: timedelta = timedelta(seconds=0),
    kid: str = "default",
) -> str:
    now = datetime.now(tz=UTC)
    claims = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "scope": "read write",
        "exp": now + expires_delta,
        "nbf": now + not_before_delta,
        "iat": now + issued_at_delta,
    }
    return jwt.encode(claims, secret, algorithm="HS256", headers={"kid": kid})


def test_auth_jwt_happy_path(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
    )

    principal = verify_bearer(token, hs_settings)

    assert principal.sub == "user-1"
    assert principal.scopes == ("read", "write")


def test_auth_jwt_expired_rejected(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
        expires_delta=timedelta(seconds=-120),
    )

    with pytest.raises(AuthError, match="Token validation failed"):
        verify_bearer(token, hs_settings)


def test_auth_jwt_clock_skew_within_60s_accepted(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
        expires_delta=timedelta(seconds=-30),
    )

    principal = verify_bearer(token, hs_settings)

    assert principal.sub == "user-1"


def test_auth_jwt_clock_skew_beyond_60s_rejected(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
        expires_delta=timedelta(seconds=-61),
    )

    with pytest.raises(AuthError, match="Token validation failed"):
        verify_bearer(token, hs_settings)


def test_auth_jwt_future_iat_rejected(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
        issued_at_delta=timedelta(seconds=120),
    )

    with pytest.raises(AuthError, match="Token validation failed"):
        verify_bearer(token, hs_settings)


def test_auth_jwt_audience_mismatch_rejected(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience="wrong-aud",
    )

    with pytest.raises(AuthError, match="Token validation failed"):
        verify_bearer(token, hs_settings)


def test_auth_jwt_issuer_mismatch_rejected(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer="https://other-issuer.example",
        audience=hs_settings.audience,
    )

    with pytest.raises(AuthError, match="Token validation failed"):
        verify_bearer(token, hs_settings)


def test_auth_jwt_alg_none_rejected(hs_settings: JwtValidationSettings) -> None:
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": hs_settings.issuer,
            "aud": hs_settings.audience,
            "exp": now + timedelta(minutes=1),
            "nbf": now,
            "iat": now,
        },
        key="",
        algorithm="none",
        headers={"kid": "default"},
    )

    with pytest.raises(AuthError, match="alg=none"):
        verify_bearer(token, hs_settings)


def test_auth_jwt_kid_traversal_rejected(hs_settings: JwtValidationSettings) -> None:
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": hs_settings.issuer,
            "aud": hs_settings.audience,
            "exp": now + timedelta(minutes=1),
            "nbf": now,
            "iat": now,
        },
        key=TEST_HS_KEY,
        algorithm="HS256",
        headers={"kid": "../../etc/passwd"},
    )

    with pytest.raises(AuthError, match="Invalid token kid"):
        verify_bearer(token, hs_settings)


def test_auth_authorization_header_uses_bearer_scheme(hs_settings: JwtValidationSettings) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
    )

    principal = verify_authorization_header(f"Bearer {token}", hs_settings)

    assert principal.sub == "user-1"


def test_auth_authorization_header_rejects_wrong_scheme(hs_settings: JwtValidationSettings) -> None:
    with pytest.raises(AuthError, match="scheme"):
        verify_authorization_header("Basic deadbeef", hs_settings)


def test_auth_authorization_header_accepts_case_insensitive_bearer(
    hs_settings: JwtValidationSettings,
) -> None:
    token = _mint_hs_token(
        secret=TEST_HS_KEY,
        issuer=hs_settings.issuer,
        audience=hs_settings.audience,
    )

    lower = verify_authorization_header(f"bearer {token}", hs_settings)
    upper = verify_authorization_header(f"BEARER {token}", hs_settings)

    assert lower.sub == "user-1"
    assert upper.sub == "user-1"
