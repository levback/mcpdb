from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final

SECRET_REF_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\$\{(env|vault):([^}]+)\}$")
LOGGER = logging.getLogger(__name__)


class SecretResolutionError(ValueError):
    """Raised when a SecretRef cannot be resolved."""


@dataclass(frozen=True)
class SecretRef:
    """Represents a parsed SecretRef such as ${env:NAME} or ${vault:path}."""

    provider: str
    key: str

    @classmethod
    def parse(cls, value: str) -> SecretRef | None:
        match = SECRET_REF_PATTERN.fullmatch(value)
        if match is None:
            return None
        return cls(provider=match.group(1), key=match.group(2))


class VaultProvider(ABC):
    """Abstract provider for ${vault:*} SecretRef resolution."""

    @abstractmethod
    def resolve(self, key: str) -> str:
        """Resolve a key to a secret value."""


class EnvProvider:
    """Environment-based SecretRef resolver with case-insensitive lookup."""

    def resolve(self, key: str) -> str:
        normalized = key.casefold()
        for env_name, env_value in os.environ.items():
            if env_name.casefold() == normalized:
                return env_value
        raise SecretResolutionError(f"Required environment variable is missing: {key}")


class MemoryVault(VaultProvider):
    """In-memory fake vault for tests and local development."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = dict(secrets or {})

    def resolve(self, key: str) -> str:
        if key not in self._secrets:
            raise SecretResolutionError(f"Vault key is missing: {key}")
        secret_value = self._secrets[key]
        self._secrets[key] = "[REDACTED]"
        LOGGER.info("Vault key resolved: %s", key)  # OWASP A02: never log secret values
        return secret_value


def resolve_secret_ref(
    value: str,
    env_provider: EnvProvider,
    vault_provider: VaultProvider | None,
) -> str:
    secret_ref = SecretRef.parse(value)
    if secret_ref is None:
        return value
    if secret_ref.provider == "env":
        return env_provider.resolve(secret_ref.key)
    if vault_provider is None:
        raise SecretResolutionError(f"Vault provider is not configured for key: {secret_ref.key}")
    return vault_provider.resolve(secret_ref.key)
