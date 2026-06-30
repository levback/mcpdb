from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from mcpdb.config.models import McpDbSettings
from mcpdb.config.secrets import (
    EnvProvider,
    SecretResolutionError,
    VaultProvider,
    resolve_secret_ref,
)
from mcpdb.config.validators import format_validation_error

DISCOVERY_PATHS = [
    Path("mcpdb.yaml"),
    Path.home() / ".config" / "mcpdb" / "config.yaml",
    Path("/etc/mcpdb/config.yaml"),
]


class ConfigLoadError(ValueError):
    """Raised when config file loading or validation fails."""


def _raise_on_duplicate_keys(node: Any, path: str = "root") -> None:
    if isinstance(node, yaml.nodes.MappingNode):
        seen_keys: set[Any] = set()
        for key_node, value_node in node.value:
            key = getattr(key_node, "value", None)
            if key in seen_keys:
                raise ConfigLoadError(f"Duplicate YAML key detected at {path}: {key}")
            seen_keys.add(key)
            _raise_on_duplicate_keys(value_node, f"{path}.{key}")
        return
    if isinstance(node, yaml.nodes.SequenceNode):
        for index, child in enumerate(node.value):
            _raise_on_duplicate_keys(child, f"{path}[{index}]")


def _discover_path() -> Path:
    for candidate in DISCOVERY_PATHS:
        if candidate.is_file():
            return candidate
    raise ConfigLoadError("No config file found in discovery paths")


def _resolve_tree(
    value: Any,
    env_provider: EnvProvider,
    vault_provider: VaultProvider | None,
    path: str,
) -> Any:
    if isinstance(value, str):
        try:
            return resolve_secret_ref(value, env_provider, vault_provider)
        except SecretResolutionError as error:
            raise ConfigLoadError(f"Unresolved SecretRef at {path}: {error}") from error
    if isinstance(value, list):
        return [
            _resolve_tree(item, env_provider, vault_provider, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _resolve_tree(item, env_provider, vault_provider, f"{path}.{key}")
            for key, item in value.items()
        }
    return value


def _apply_env_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    prefix = "MCPDB__"

    for env_name, env_value in os.environ.items():
        if not env_name.startswith(prefix):
            continue
        path_parts = [part.lower() for part in env_name[len(prefix) :].split("__") if part]
        if not path_parts:
            continue

        target: dict[str, Any] = updated
        for key in path_parts[:-1]:
            child = target.get(key)
            if not isinstance(child, dict):
                child = {}
                target[key] = child
            target = child
        target[path_parts[-1]] = yaml.safe_load(env_value)

    return updated


def load_settings(
    path: Path | str | None,
    *,
    env_provider: EnvProvider | None = None,
    vault_provider: VaultProvider | None = None,
) -> McpDbSettings:
    env_provider = env_provider or EnvProvider()
    config_path = Path(path) if path is not None else _discover_path()
    if not config_path.is_file():
        raise ConfigLoadError(f"Config file does not exist: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    try:
        composed = yaml.compose(text)
        if composed is not None:
            _raise_on_duplicate_keys(composed)
        raw_data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConfigLoadError(f"Malformed YAML in {config_path}: {error}") from error

    payload = raw_data if isinstance(raw_data, dict) else {}
    resolved_payload = _resolve_tree(payload, env_provider, vault_provider, "root")
    resolved_payload = _apply_env_overrides(resolved_payload)  # NIST SC-12: env precedence

    try:
        return McpDbSettings.model_validate(resolved_payload)
    except ValidationError as error:
        raise ConfigLoadError(format_validation_error(error)) from error
