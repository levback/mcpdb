from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from mcpdb.security.auth import AuthError, JwtValidationSettings, verify_bearer

TEST_HS_KEY = "0123456789abcdef0123456789abcdef"


def test_security_owasp_a07_alg_confusion_attempt() -> None:
    settings = JwtValidationSettings(
        issuer="https://issuer.example",
        audience="mcpdb-client",
        algorithms=("RS256",),
        public_keys={"default": "-----BEGIN PUBLIC KEY-----\nMIIB\n-----END PUBLIC KEY-----"},
    )
    token = jwt.encode(
        {
            "sub": "alice",
            "iss": settings.issuer,
            "aud": settings.audience,
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
            "nbf": datetime.now(tz=UTC),
            "iat": datetime.now(tz=UTC),
        },
        TEST_HS_KEY,
        algorithm="HS256",
        headers={"kid": "default"},
    )

    with pytest.raises(AuthError, match="Algorithm"):
        verify_bearer(token, settings)


def test_security_owasp_a07_kid_path_traversal_rejected() -> None:
    settings = JwtValidationSettings(
        issuer="https://issuer.example",
        audience="mcpdb-client",
        algorithms=("HS256",),
        hs_secrets={"default": TEST_HS_KEY},
    )
    token = jwt.encode(
        {
            "sub": "alice",
            "iss": settings.issuer,
            "aud": settings.audience,
            "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
            "nbf": datetime.now(tz=UTC),
            "iat": datetime.now(tz=UTC),
        },
        TEST_HS_KEY,
        algorithm="HS256",
        headers={"kid": "..\\..\\secrets"},
    )

    with pytest.raises(AuthError, match="Invalid token kid"):
        verify_bearer(token, settings)
