from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcpdb.config.validators import (
    validate_limits_constraints,
    validate_profile_constraints,
    validate_security_constraints,
)

Backend = Literal["postgres", "mysql", "sqlite", "mongodb"]
Mode = Literal["read_only", "read_write"]
Transport = Literal["stdio", "http"]


class Limits(BaseModel):
    query_timeout_ms: int = 30_000
    max_rows: int = 10_000
    max_payload_bytes: int = 5_000_000

    @model_validator(mode="after")
    def validate_caps(self) -> Limits:
        validate_limits_constraints(self.query_timeout_ms, self.max_rows)
        return self


class Security(BaseModel):
    auth_enabled: bool = False
    bind_address: str = "127.0.0.1"

    @model_validator(mode="after")
    def validate_security(self) -> Security:
        validate_security_constraints(self.bind_address, self.auth_enabled)
        return self


class McpSettings(BaseModel):
    transport: Transport = "stdio"


class Profile(BaseModel):
    name: str = Field(min_length=1)
    backend: Backend
    mode: Mode = "read_only"
    allow_writes: bool = False
    dsn: SecretStr | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: SecretStr | None = None

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if not 1 <= value <= 65535:
            raise ValueError("port must be within [1, 65535]")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> Profile:
        has_dsn = self.dsn is not None
        has_discrete = self.host is not None and self.database is not None
        if has_dsn == has_discrete:
            raise ValueError("profile must provide either dsn or host+database")
        validate_profile_constraints(self.mode, self.allow_writes, self.name)
        return self


class McpDbSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCPDB__",
        env_nested_delimiter="__",
        extra="forbid",
    )

    profiles: list[Profile] = Field(default_factory=list)
    security: Security = Field(default_factory=Security)
    limits: Limits = Field(default_factory=Limits)
    mcp: McpSettings = Field(default_factory=McpSettings)

    @model_validator(mode="after")
    def validate_profile_uniqueness(self) -> McpDbSettings:
        names = [profile.name for profile in self.profiles]
        if len(set(names)) != len(names):
            raise ValueError("profile names must be unique")
        return self

    def __repr__(self) -> str:
        redacted_dump = _redact_secrets(self.model_dump(mode="python"))
        return f"McpDbSettings({redacted_dump})"  # OWASP A02: redact secret material


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, SecretStr):
        return "**********"
    if isinstance(value, dict):
        return {key: _redact_secrets(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_redact_secrets(child) for child in value]
    return value
