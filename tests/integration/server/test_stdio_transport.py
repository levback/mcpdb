from __future__ import annotations

from contextlib import suppress

import anyio
import pytest
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.client.session import ClientSession
from pydantic import SecretStr

from mcpdb.config.models import McpDbSettings, Profile
from mcpdb.db.fake import FakeConnector
from mcpdb.server.app import build_server


async def _run_server(
    server,
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
) -> None:
    await server.run(read_stream, write_stream, server.create_initialization_options())


@pytest.mark.asyncio
async def test_integration_stdio_lists_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    import mcpdb.server.app as app_module

    monkeypatch.setattr(
        app_module,
        "_build_connector",
        lambda profile: FakeConnector(latency_ms=0.5),
    )

    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ]
    )
    server = build_server(settings)

    client_to_server_send, client_to_server_recv = anyio.create_memory_object_stream(64)
    server_to_client_send, server_to_client_recv = anyio.create_memory_object_stream(64)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(_run_server, server, client_to_server_recv, server_to_client_send)
        async with ClientSession(server_to_client_recv, client_to_server_send) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            assert tool_names == ["db_introspect", "db_list_profiles", "db_ping", "db_query"]

        task_group.cancel_scope.cancel()
        with suppress(Exception):
            await client_to_server_send.aclose()
            await server_to_client_send.aclose()


@pytest.mark.asyncio
async def test_integration_stdio_invokes_db_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    import mcpdb.server.app as app_module

    monkeypatch.setattr(
        app_module,
        "_build_connector",
        lambda profile: FakeConnector(latency_ms=0.5),
    )

    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ]
    )
    server = build_server(settings)

    client_to_server_send, client_to_server_recv = anyio.create_memory_object_stream(64)
    server_to_client_send, server_to_client_recv = anyio.create_memory_object_stream(64)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(_run_server, server, client_to_server_recv, server_to_client_send)
        async with ClientSession(server_to_client_recv, client_to_server_send) as session:
            await session.initialize()
            result = await session.call_tool("db_ping", {"profile": "main"})
            assert result.isError is False

        task_group.cancel_scope.cancel()
        with suppress(Exception):
            await client_to_server_send.aclose()
            await server_to_client_send.aclose()
