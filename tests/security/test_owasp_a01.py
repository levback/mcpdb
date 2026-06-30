from __future__ import annotations

from pathlib import Path

import jwt

from mcpdb.security.auth import JwtValidationSettings, verify_bearer
from mcpdb.security.authz import load_policy_enforcer

TEST_HS_KEY = "0123456789abcdef0123456789abcdef"


def test_security_owasp_a01_try_bypass_with_extra_claim(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
rules:
  - subjects: ["*"]
    actions: ["db_query"]
    resources: ["prod"]
    effect: deny
""",
        encoding="utf-8",
    )
    enforcer = load_policy_enforcer(policy_path)

    settings = JwtValidationSettings(
        issuer="https://issuer.example",
        audience="mcpdb-client",
        algorithms=("HS256",),
        hs_secrets={"default": TEST_HS_KEY},
    )
    token = jwt.encode(
        {
            "sub": "alice",
            "role": "admin",
            "iss": settings.issuer,
            "aud": settings.audience,
            "exp": 4102444800,
            "nbf": 1700000000,
            "iat": 1700000000,
        },
        TEST_HS_KEY,
        algorithm="HS256",
        headers={"kid": "default"},
    )

    principal = verify_bearer(token, settings)
    decision = enforcer.authorize(principal.sub, "db_query", "prod")

    assert principal.sub == "alice"
    assert decision.allowed is False
