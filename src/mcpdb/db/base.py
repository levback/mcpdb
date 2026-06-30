from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Context:
    """Runtime Context passed to Connector operations."""

    profile: str
    request_id: str
    principal: str


@dataclass(frozen=True)
class Cap:
    query_timeout_ms: int
    max_rows: int
    max_payload_bytes: int


@dataclass(frozen=True)
class OperationResult:
    rows: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    row_count: int = 0
    payload_bytes: int = 0
    latency_ms: float = 0.0
    truncated: bool = False


class DbError(RuntimeError):
    """Base database abstraction error."""


class ConnectionFailure(DbError):  # noqa: N818 - required by phase spec
    """Raised for connect/close failures."""


class QueryFailure(DbError):  # noqa: N818 - required by phase spec
    """Raised for query and introspection failures."""


class PolicyRefused(DbError):  # noqa: N818 - required by phase spec
    """Raised when Policy denies an Operation Class."""


class RegistryError(DbError):
    """Raised for backend registration errors."""


@runtime_checkable
class Connector(Protocol):
    async def connect(self, context: Context) -> None: ...

    async def close(self, context: Context) -> None: ...

    async def ping(self, context: Context) -> float: ...

    async def execute(
        self,
        context: Context,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> OperationResult: ...

    async def introspect(
        self,
        context: Context,
        target: str | None = None,
    ) -> OperationResult: ...

    async def transaction(self, context: Context) -> None: ...
