from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Literal

import yaml

Effect = Literal["allow", "deny"]


class AuthzPolicyError(ValueError):
    """Raised when policy schema is invalid."""


@dataclass(frozen=True)
class PolicyRule:
    subjects: tuple[str, ...]
    actions: tuple[str, ...]
    resources: tuple[str, ...]
    effect: Effect


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


class PolicyEnforcer:
    def __init__(self, rules: list[PolicyRule]) -> None:
        self._rules = list(rules)

    def authorize(self, subject: str, action: str, resource: str) -> AuthorizationDecision:
        specific_rules = [
            rule
            for rule in self._matching_rules(subject, action, resource)
            if subject in rule.subjects
        ]
        if any(rule.effect == "allow" for rule in specific_rules):
            return AuthorizationDecision(True, "allowed by subject rule")  # OWASP A01
        if any(rule.effect == "deny" for rule in specific_rules):
            return AuthorizationDecision(False, "denied by subject rule")  # OWASP A01

        wildcard_rules = [
            rule for rule in self._matching_rules(subject, action, resource) if "*" in rule.subjects
        ]
        if any(rule.effect == "deny" for rule in wildcard_rules):
            return AuthorizationDecision(False, "denied by wildcard rule")  # OWASP A01
        if any(rule.effect == "allow" for rule in wildcard_rules):
            return AuthorizationDecision(True, "allowed by wildcard rule")

        return AuthorizationDecision(False, "default deny")  # OWASP A01

    def _matching_rules(self, subject: str, action: str, resource: str) -> list[PolicyRule]:
        return [
            rule
            for rule in self._rules
            if _matches_token(subject, rule.subjects)
            and _matches_token(action, rule.actions)
            and _matches_resource(resource, rule.resources)
        ]


def load_policy_enforcer(path: Path) -> PolicyEnforcer:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AuthzPolicyError(f"Policy file not found: {path}") from error

    if not isinstance(payload, dict):
        raise AuthzPolicyError("Policy must be a mapping")

    rules_payload = payload.get("rules")
    if not isinstance(rules_payload, list) or not rules_payload:
        raise AuthzPolicyError("Policy must define non-empty rules")

    rules: list[PolicyRule] = []
    for raw_rule in rules_payload:
        if not isinstance(raw_rule, dict):
            raise AuthzPolicyError("Each rule must be a mapping")
        subjects = _require_string_list(raw_rule, "subjects")
        actions = _require_string_list(raw_rule, "actions")
        resources = _require_string_list(raw_rule, "resources")
        effect_raw = raw_rule.get("effect")
        if effect_raw not in ("allow", "deny"):
            raise AuthzPolicyError("effect must be 'allow' or 'deny'")
        rules.append(
            PolicyRule(
                subjects=tuple(subjects),
                actions=tuple(actions),
                resources=tuple(resources),
                effect=effect_raw,
            )
        )

    return PolicyEnforcer(rules)


def _require_string_list(payload: dict[str, object], field: str) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise AuthzPolicyError(f"{field} must be a non-empty list of strings")
    return [item for item in value if item]


def _matches_token(value: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern == "*" or pattern == value for pattern in patterns)


def _matches_resource(value: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(value, pattern) for pattern in patterns)
