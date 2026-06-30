from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from mcpdb.db.base import ConnectionFailure, Connector, Context, OperationResult, QueryFailure


@dataclass(frozen=True)
class FakeFailure:
    mode: str
    remaining_calls: int


class FakeConnector(Connector):
    def __init__(self, *, latency_ms: float = 1.0) -> None:
        self._latency_ms = latency_ms
        self._failure: FakeFailure | None = None
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    @property
    def calls(self) -> tuple[tuple[str, tuple[Any, ...], dict[str, Any]], ...]:
        return tuple(self._calls)

    def set_failure(self, mode: str, n_calls: int) -> None:
        self._failure = FakeFailure(mode=mode, remaining_calls=n_calls)

    def _record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self._calls.append((name, args, kwargs))

    def _maybe_fail(self, mode: str) -> None:
        if self._failure is None or self._failure.mode != mode:
            return

        remaining = self._failure.remaining_calls
        if remaining <= 0:
            return

        self._failure = FakeFailure(mode=mode, remaining_calls=remaining - 1)
        if mode in {"connect", "close", "ping"}:
            raise ConnectionFailure(f"Injected fake failure in {mode}")
        raise QueryFailure(f"Injected fake failure in {mode}")

    async def connect(self, context: Context) -> None:
        self._record("connect", context)
        self._maybe_fail("connect")

    async def close(self, context: Context) -> None:
        self._record("close", context)
        self._maybe_fail("close")

    async def ping(self, context: Context) -> float:
        self._record("ping", context)
        self._maybe_fail("ping")
        return self._latency_ms

    async def execute(
        self,
        context: Context,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> OperationResult:
        self._record("execute", context, statement, parameters)
        self._maybe_fail("execute")
        rows = ({"statement": statement, "parameters": dict(parameters or {})},)
        return OperationResult(
            rows=rows,
            row_count=1,
            payload_bytes=len(statement),
            latency_ms=self._latency_ms,
        )

    async def introspect(self, context: Context, target: str | None = None) -> OperationResult:
        self._record("introspect", context, target)
        self._maybe_fail("introspect")
        rows = ({"target": target or "all", "kind": "fake"},)
        return OperationResult(
            rows=rows,
            row_count=1,
            payload_bytes=32,
            latency_ms=self._latency_ms,
        )

    async def transaction(self, context: Context) -> None:
        self._record("transaction", context)
        self._maybe_fail("transaction")
