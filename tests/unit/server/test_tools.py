from __future__ import annotations

import mcp.types as types
import pytest

from mcpdb.db.base import Context as DbContext
from mcpdb.db.base import OperationResult, PolicyRefused, QueryFailure
from mcpdb.db.fake import FakeConnector
from mcpdb.db.policy import Policy
from mcpdb.server.context import RequestContext
from mcpdb.server.tools import ProfileToolBinding, ToolService, register_tools


class FakeSqlConnector(FakeConnector):
    async def execute(self, context: DbContext, statement: str, parameters=None) -> OperationResult:
        payload = dict(parameters or {})
        if statement.lower().startswith("select"):
            rows = ({"id": 1, "params": payload}, {"id": 2, "params": payload})
            return OperationResult(rows=rows, row_count=2, payload_bytes=64, latency_ms=1.0)
        if statement.lower().startswith("grant"):
            raise PolicyRefused("ADMIN denied")
        if statement.lower().startswith("insert"):
            return OperationResult(rows=(), row_count=1, payload_bytes=16, latency_ms=1.0)
        raise QueryFailure("unsupported SQL")

    async def introspect(self, context: DbContext, target: str | None = None) -> OperationResult:
        return OperationResult(rows=({"column": "id", "type": "integer"},), row_count=1)


class FakeMongoConnector(FakeConnector):
    async def execute(self, context: DbContext, statement: str, parameters=None) -> OperationResult:
        payload = dict(parameters or {})
        if statement == "find":
            return OperationResult(rows=({"name": "alice", "payload": payload},), row_count=1)
        if statement == "server_status":
            return OperationResult(rows=({"ok": 1},), row_count=1)
        raise QueryFailure("unknown operation")


@pytest.fixture
def tool_service() -> ToolService:
    return ToolService(
        {
            "sql": ProfileToolBinding(
                profile="sql",
                backend="postgres",
                connector=FakeSqlConnector(),
                policy=Policy(allow_reads=True, allow_writes=False, allow_admin=False, max_rows=1),
            ),
            "mongo": ProfileToolBinding(
                profile="mongo",
                backend="mongodb",
                connector=FakeMongoConnector(),
                policy=Policy(allow_reads=True, allow_writes=True, allow_admin=False, max_rows=10),
            ),
        }
    )


@pytest.mark.asyncio
async def test_tools_db_query_sql_uses_bound_params(tool_service: ToolService) -> None:
    result = await tool_service.db_query(
        profile="sql",
        statement="SELECT * FROM users WHERE id=:id",
        parameters={"id": 1},
        request=RequestContext(correlation_id="c1", principal="alice"),
    )

    assert result["row_count"] == 2
    assert result["rows"][0]["params"] == {"id": 1}


@pytest.mark.asyncio
async def test_tools_db_query_mongo_uses_filter_model(tool_service: ToolService) -> None:
    result = await tool_service.db_query(
        profile="mongo",
        operation="find",
        collection="users",
        filter_doc={"name": {"$eq": "alice"}},
        projection={"name": 1},
        limit=5,
        request=RequestContext(correlation_id="c2", principal="alice"),
    )

    assert result["row_count"] == 1
    assert result["rows"][0]["name"] == "alice"


@pytest.mark.asyncio
async def test_tools_db_introspect_returns_columns(tool_service: ToolService) -> None:
    result = await tool_service.db_introspect(
        profile="sql",
        target="users",
        request=RequestContext(correlation_id="c3", principal="alice"),
    )

    assert result["rows"][0]["column"] == "id"


@pytest.mark.asyncio
async def test_tools_db_ping_measures_latency(tool_service: ToolService) -> None:
    result = await tool_service.db_ping(
        profile="sql",
        request=RequestContext(correlation_id="c4", principal="alice"),
    )

    assert result["backend"] == "postgres"
    assert result["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_tools_db_list_profiles_does_not_leak_creds(tool_service: ToolService) -> None:
    result = await tool_service.db_list_profiles()

    assert result == {
        "profiles": [
            {"name": "mongo", "backend": "mongodb"},
            {"name": "sql", "backend": "postgres"},
        ]
    }


@pytest.mark.asyncio
async def test_tools_db_query_read_only_denies_write(tool_service: ToolService) -> None:
    with pytest.raises(PolicyRefused):
        await tool_service.db_query(
            profile="sql",
            statement="INSERT INTO users(id) VALUES (:id)",
            parameters={"id": 2},
            request=RequestContext(correlation_id="c5", principal="alice"),
        )


@pytest.mark.asyncio
async def test_tools_db_query_admin_requires_admin_op_class(tool_service: ToolService) -> None:
    with pytest.raises(PolicyRefused):
        await tool_service.db_query(
            profile="sql",
            statement="GRANT SELECT ON users TO reader",
            parameters={},
            request=RequestContext(correlation_id="c6", principal="alice"),
        )


@pytest.mark.asyncio
async def test_tools_db_query_row_cap_applied(tool_service: ToolService) -> None:
    result = await tool_service.db_query(
        profile="sql",
        statement="SELECT * FROM users",
        parameters={},
        request=RequestContext(correlation_id="c7", principal="alice"),
    )

    assert result["row_count"] == 2


@pytest.mark.asyncio
async def test_tools_db_query_timeout_returned_as_error(tool_service: ToolService) -> None:
    error_result = await tool_service.dispatch(
        "db_query",
        {
            "profile": "sql",
            "statement": "BAD",
            "correlation_id": "c8",
            "principal": "alice",
        },
    )

    assert isinstance(error_result, types.CallToolResult)
    assert error_result.isError is True


@pytest.mark.asyncio
async def test_tools_dispatch_unknown_tool_returns_mapped_error(tool_service: ToolService) -> None:
    error_result = await tool_service.dispatch("unknown", {"correlation_id": "c9"})

    assert isinstance(error_result, types.CallToolResult)
    assert error_result.isError is True


def test_tools_param_validation() -> None:
    service = ToolService({})

    with pytest.raises(ValueError):
        service._as_optional_str(3)  # noqa: SLF001 - unit coverage for input validation helper


def test_tools_optional_dict_and_int_validation() -> None:
    service = ToolService({})

    assert service._as_optional_dict({"x": 1}) == {"x": 1}
    assert service._as_optional_dict(None) is None
    assert service._as_optional_int(5) == 5
    assert service._as_optional_int(None) is None

    with pytest.raises(ValueError):
        service._as_optional_dict("bad")

    with pytest.raises(ValueError):
        service._as_optional_int("bad")


def test_tools_projection_validation() -> None:
    service = ToolService({})

    assert service._as_projection({"name": 1, "age": False}) == {"name": 1, "age": 0}
    assert service._as_projection(None) is None

    with pytest.raises(ValueError):
        service._as_projection({"": 1})

    with pytest.raises(ValueError):
        service._as_projection({"name": 2})


def test_tools_request_context_defaults() -> None:
    service = ToolService({})

    request = service._request_context({})

    assert request.correlation_id == "tool-request"
    assert request.principal == "anonymous"


def test_tools_request_context_ignores_spoofed_identity_metadata() -> None:
    service = ToolService({})

    request = service._request_context(
        {
            "correlation_id": "evil-correlation",
            "principal": "admin",
            "source_ip": "203.0.113.10",
            "user_agent": "spoofed-client",
        }
    )

    assert request.correlation_id == "tool-request"
    assert request.principal == "anonymous"
    assert request.source_ip == "127.0.0.1"
    assert request.user_agent == "mcp-client"


def test_tools_operation_class_helpers() -> None:
    service = ToolService({})

    assert service._sql_op_class("SELECT 1")
    assert service._sql_op_class("INSERT INTO x VALUES (1)")
    assert service._sql_op_class("/* hidden */ DROP TABLE x")
    assert service._sql_op_class("-- noop\nDELETE FROM x")
    assert service._sql_op_class("GRANT SELECT ON x TO y")
    assert service._mongo_op_class("find")
    assert service._mongo_op_class("insert_one")
    assert service._mongo_op_class("server_status")

    assert service._sql_op_class("/* hidden */ DROP TABLE x").value == "WRITE"
    assert service._sql_op_class("-- noop\nDELETE FROM x").value == "WRITE"

    with pytest.raises(QueryFailure):
        service._mongo_op_class("unknown")


@pytest.mark.asyncio
async def test_tools_register_tools_handlers() -> None:
    service = ToolService(
        {
            "sql": ProfileToolBinding(
                profile="sql",
                backend="postgres",
                connector=FakeSqlConnector(),
                policy=Policy(allow_reads=True),
            )
        }
    )

    class FakeServer:
        def __init__(self) -> None:
            self.request_handlers: dict[object, object] = {}

    fake_server = FakeServer()
    register_tools(fake_server, service)

    list_handler = fake_server.request_handlers[types.ListToolsRequest]
    call_handler = fake_server.request_handlers[types.CallToolRequest]

    list_result = await list_handler(types.ListToolsRequest())
    call_result = await call_handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(name="db_list_profiles", arguments={})
        )
    )

    assert len(list_result.root.tools) == 4
    assert call_result.root.isError is False
