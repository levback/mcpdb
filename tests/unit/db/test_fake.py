import pytest

from mcpdb.db.base import ConnectionFailure, Context, QueryFailure
from mcpdb.db.fake import FakeConnector


@pytest.mark.asyncio
async def test_fake_records_all_calls_with_args_kwargs() -> None:
    connector = FakeConnector(latency_ms=3.5)
    context = Context(profile="default", request_id="r-1", principal="tester")

    await connector.connect(context)
    await connector.execute(context, "select 1", {"x": 1})
    await connector.introspect(context, "users")
    await connector.transaction(context)
    await connector.close(context)

    names = [entry[0] for entry in connector.calls]
    assert names == ["connect", "execute", "introspect", "transaction", "close"]


@pytest.mark.asyncio
async def test_fake_injects_transient_failure_then_recovers() -> None:
    connector = FakeConnector()
    context = Context(profile="default", request_id="r-1", principal="tester")
    connector.set_failure("execute", 1)

    with pytest.raises(QueryFailure):
        await connector.execute(context, "select 1")

    result = await connector.execute(context, "select 2")
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_fake_ping_returns_configured_latency_ms() -> None:
    connector = FakeConnector(latency_ms=12.5)
    context = Context(profile="default", request_id="r-1", principal="tester")

    latency = await connector.ping(context)

    assert latency == 12.5


@pytest.mark.asyncio
async def test_fake_connection_failure_mode() -> None:
    connector = FakeConnector()
    context = Context(profile="default", request_id="r-1", principal="tester")
    connector.set_failure("connect", 1)

    with pytest.raises(ConnectionFailure):
        await connector.connect(context)
