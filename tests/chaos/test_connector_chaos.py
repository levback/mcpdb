from __future__ import annotations

import asyncio

import pytest

from mcpdb.db.base import Context, QueryFailure
from mcpdb.db.fake import FakeConnector


@pytest.mark.asyncio
async def test_chaos_transient_failure_does_not_corrupt_state() -> None:
    connector = FakeConnector(latency_ms=0.5)
    connector.set_failure("execute", 1)
    context = Context(profile="chaos", request_id="req-1", principal="tester")

    with pytest.raises(QueryFailure):
        await connector.execute(context, "SELECT 1")

    recovered = await connector.execute(context, "SELECT 2")
    assert recovered.row_count == 1
    names = [entry[0] for entry in connector.calls]
    assert names.count("execute") == 2


@pytest.mark.asyncio
async def test_chaos_timeout_is_observable_and_cancellable() -> None:
    context = Context(profile="chaos", request_id="req-2", principal="tester")

    class SlowFakeConnector(FakeConnector):
        async def execute(self, context: Context, statement: str, parameters=None):
            _ = parameters
            await asyncio.sleep(0.2)
            return await super().execute(context, statement, parameters)

    connector = SlowFakeConnector()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            connector.execute(context, "SELECT 1"),
            timeout=0.01,
        )
