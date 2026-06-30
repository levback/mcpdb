from __future__ import annotations

from pathlib import Path

import pytest

from mcpdb.security.authz import AuthzPolicyError, load_policy_enforcer


def _write_policy(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_authz_default_deny(tmp_path: Path) -> None:
    policy = _write_policy(
        tmp_path / "policy.yaml",
        """
rules:
  - subjects: ["alice"]
    actions: ["db_ping"]
    resources: ["prod"]
    effect: allow
""",
    )

    enforcer = load_policy_enforcer(policy)
    decision = enforcer.authorize("bob", "db_ping", "prod")

    assert decision.allowed is False


def test_authz_allow_overrides_deny_for_specific_subject(tmp_path: Path) -> None:
    policy = _write_policy(
        tmp_path / "policy.yaml",
        """
rules:
  - subjects: ["*"]
    actions: ["db_query"]
    resources: ["prod"]
    effect: deny
  - subjects: ["alice"]
    actions: ["db_query"]
    resources: ["prod"]
    effect: allow
""",
    )

    enforcer = load_policy_enforcer(policy)

    assert enforcer.authorize("alice", "db_query", "prod").allowed is True
    assert enforcer.authorize("bob", "db_query", "prod").allowed is False


def test_authz_resource_glob_matches_profile(tmp_path: Path) -> None:
    policy = _write_policy(
        tmp_path / "policy.yaml",
        """
rules:
  - subjects: ["alice"]
    actions: ["db_introspect"]
    resources: ["prod_*"]
    effect: allow
""",
    )

    enforcer = load_policy_enforcer(policy)

    assert enforcer.authorize("alice", "db_introspect", "prod_main").allowed is True
    assert enforcer.authorize("alice", "db_introspect", "dev_main").allowed is False


def test_authz_unknown_action_rejected(tmp_path: Path) -> None:
    policy = _write_policy(
        tmp_path / "policy.yaml",
        """
rules:
  - subjects: ["alice"]
    actions: ["db_ping"]
    resources: ["*"]
    effect: allow
""",
    )

    enforcer = load_policy_enforcer(policy)

    assert enforcer.authorize("alice", "unknown_action", "prod").allowed is False


def test_authz_invalid_policy_raises(tmp_path: Path) -> None:
    broken_policy = _write_policy(
        tmp_path / "policy.yaml",
        """
rules:
  - subjects: "alice"
    actions: ["db_ping"]
    resources: ["*"]
    effect: allow
""",
    )

    with pytest.raises(AuthzPolicyError, match="subjects"):
        load_policy_enforcer(broken_policy)
