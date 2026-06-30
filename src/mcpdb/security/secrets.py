from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from mcpdb.config.secrets import SecretResolutionError, VaultProvider


class SecuritySecretError(SecretResolutionError):
    """Raised when security-layer secret resolution fails."""


class EnvVault(VaultProvider):
    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix

    def resolve(self, key: str) -> str:
        env_key = f"{self._prefix}{key}"
        if env_key not in os.environ:
            raise SecuritySecretError(f"Missing environment secret: {env_key}")
        return os.environ[env_key]


@dataclass(frozen=True)
class FileVault(VaultProvider):
    path: Path

    def resolve(self, key: str) -> str:
        stat_result = self.path.stat()
        if stat_result.st_mode & 0o077:
            raise SecuritySecretError("Vault file must have 0600 permissions")  # OWASP A02
        if (stat_result.st_mode & 0o600) != 0o600:
            raise SecuritySecretError("Vault file must grant owner read/write permissions")

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or key not in payload:
            raise SecuritySecretError(f"Missing vault key: {key}")

        value = payload[key]
        if not isinstance(value, str):
            raise SecuritySecretError(f"Vault value for {key} must be a string")
        return value


class AwsSmVault(VaultProvider):
    def __init__(self, region: str) -> None:
        self._region = region

    def resolve(self, key: str) -> str:
        raise NotImplementedError(
            f"AwsSmVault is a stub for region {self._region}; secret '{key}' is unresolved"
        )
