from __future__ import annotations

import json

import pytest

from mcpdb.db.base import ConnectionFailure, OperationResult
from mcpdb.db.base import Context as DbContext
from mcpdb.db.policy import Policy
from mcpdb.server.tools import ProfileToolBinding, ToolService


class MidCallDropConnector:
    async def connect(self, context: DbContext) -> None:
        _ = context

    async def close(self, context: DbContext) -> None:
        _ = context

    async def ping(self, context: DbContext) -> float:
        _ = context
        return 1.0

    async def execute(
        self,
        context: DbContext,
        statement: str,
        parameters=None,
    ) -> OperationResult:
        _ = (context, statement, parameters)
        raise ConnectionFailure("dropped during execution")

    async def introspect(self, context: DbContext, target: str | None = None) -> OperationResult:
        _ = (context, target)
        return OperationResult(rows=(), row_count=0)

    async def transaction(self, context: DbContext) -> None:
        _ = context


@pytest.mark.asyncio
async def test_server_mid_call_drop_maps_to_tool_error() -> None:
    service = ToolService(
        {
            "main": ProfileToolBinding(
                profile="main",
                backend="postgres",
                connector=MidCallDropConnector(),
                policy=Policy(allow_reads=True),
            )
        }
    )

    result = await service.dispatch(
        "db_query",
        {
            "profile": "main",
            "statement": "SELECT 1",
        },
    )
    assert hasattr(result, "isError")
    assert result.isError is True


def test_chaos_partial_bytes_do_not_panic_parser() -> None:
    samples = [
        b'{"jsonrpc":"2.0","method":"db_ping",',
        b'{"jsonrpc":"2.0","method":"db_ping"}',
        b"\x00\x00{",
    ]

    for sample in samples:
        try:
            json.loads(sample.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
