from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from mcpdb.db.base import Context, PolicyRefused, QueryFailure
from mcpdb.db.policy import OpClass, Policy
from mcpdb.db.registry import BackendRegistry
from mcpdb.db.sql import register_sql_connectors
from mcpdb.db.sql.base import SqlConnector, SqlQuery, UnsupportedBackendError


@dataclass
class DummyResult:
    rows_payload: list[dict[str, Any]]

    def mappings(self) -> DummyResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows_payload


class DummySqlConnector(SqlConnector):
    backend = "sqlite"
    minimum_supported_major = 3

    def __init__(self, policy: Policy) -> None:
        super().__init__(dsn="sqlite+aiosqlite:///:memory:", policy=policy)
        self.last_query: SqlQuery | None = None
        self._result_rows: list[dict[str, Any]] = [{"id": 1}, {"id": 2}, {"id": 3}]

    async def _execute_query(self, query: SqlQuery):
        self.last_query = query
        await asyncio.sleep(0)
        return DummyResult(self._result_rows)

    async def _check_server_version(self, connection) -> None:
        return None


@pytest.mark.asyncio
async def test_sql_execute_uses_bound_params() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    await connector.execute(Context("p", "r", "u"), "SELECT :value", {"value": 10})

    assert connector.last_query is not None
    assert connector.last_query.parameters == {"value": 10}


@pytest.mark.asyncio
async def test_sql_execute_injection_attempt_blocked() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    with pytest.raises(QueryFailure):
        await connector.execute(
            Context("p", "r", "u"),
            "SELECT * FROM users WHERE id = '1' OR '1'='1'",
        )


@pytest.mark.asyncio
async def test_sql_introspect_returns_expected_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    async def fake_describe(context: Context, table: str) -> list[dict[str, Any]]:
        return [{"column": "id", "type": "integer"}]

    async def fake_indexes(context: Context, table: str) -> list[dict[str, Any]]:
        return [{"index": "idx_users_id", "unique": True}]

    monkeypatch.setattr(connector, "describe_table", fake_describe)
    monkeypatch.setattr(connector, "list_indexes", fake_indexes)

    result = await connector.introspect(Context("p", "r", "u"), "users")

    assert result.row_count == 2


@pytest.mark.asyncio
async def test_sql_query_timeout_fires_and_cancels(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = DummySqlConnector(Policy(allow_reads=True, query_timeout_ms=1))

    async def slow_execute(query: SqlQuery):
        await asyncio.sleep(0.02)
        return DummyResult([])

    monkeypatch.setattr(connector, "_execute_query", slow_execute)

    with pytest.raises(QueryFailure, match="timed out"):
        await connector.execute(Context("p", "r", "u"), "SELECT 1")


@pytest.mark.asyncio
async def test_sql_row_cap_truncates_with_warning() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True, max_rows=2))

    result = await connector.execute(Context("p", "r", "u"), "SELECT 1")

    assert result.row_count == 3
    assert len(result.rows) == 2
    assert result.truncated is True


@pytest.mark.asyncio
async def test_sql_read_only_policy_denies_insert() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True, allow_writes=False))

    with pytest.raises(PolicyRefused):
        await connector.execute(
            Context("p", "r", "u"),
            "INSERT INTO users(id) VALUES (:id)",
            {"id": 1},
        )


@pytest.mark.asyncio
async def test_sql_transaction_rollback_on_policy_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = DummySqlConnector(Policy(allow_reads=True, allow_writes=False))

    class FakeTransaction:
        def __init__(self) -> None:
            self.rollback_called = False
            self.commit_called = False

        async def rollback(self) -> None:
            self.rollback_called = True

        async def commit(self) -> None:
            self.commit_called = True

    class FakeConnection:
        def __init__(self) -> None:
            self.tx = FakeTransaction()

        async def begin(self) -> FakeTransaction:
            return self.tx

    fake_connection = FakeConnection()

    async def fake_get_connection():
        return fake_connection

    monkeypatch.setattr(connector, "_connection", fake_get_connection)

    with pytest.raises(PolicyRefused):
        async with connector.transaction_context(Context("p", "r", "u")):
            raise PolicyRefused("denied")

    assert fake_connection.tx.rollback_called is True
    assert fake_connection.tx.commit_called is False


@pytest.mark.asyncio
async def test_sql_introspect_without_target_lists_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    async def fake_list_tables(context: Context) -> list[dict[str, Any]]:
        return [{"table": "users"}, {"table": "orders"}]

    monkeypatch.setattr(connector, "list_tables", fake_list_tables)

    result = await connector.introspect(Context("p", "r", "u"))

    assert result.row_count == 2
    assert result.rows[0]["table"] == "users"


@pytest.mark.asyncio
async def test_sql_sqlite_helpers_for_schema_table_and_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    async def fake_run_rows(statement: str, params=None) -> list[dict[str, Any]]:
        if "sqlite_master" in statement:
            return [{"table_name": "items"}]
        if "PRAGMA table_info" in statement:
            return [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "notnull": 1,
                    "dflt_value": None,
                }
            ]
        if "PRAGMA index_list" in statement:
            return [{"name": "idx_items_id", "unique": 1}]
        return []

    monkeypatch.setattr(connector, "_run_rows", fake_run_rows)

    schemas = await connector.list_schemas(Context("p", "r", "u"))
    tables = await connector.list_tables(Context("p", "r", "u"))
    columns = await connector.describe_table(Context("p", "r", "u"), "items")
    indexes = await connector.list_indexes(Context("p", "r", "u"), "items")

    assert schemas == [{"schema": "main"}]
    assert tables == [{"table": "items"}]
    assert columns[0]["column"] == "id"
    assert indexes[0]["index"] == "idx_items_id"


@pytest.mark.asyncio
async def test_sql_sample_rows_clamps_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))
    captured: dict[str, Any] = {}

    async def fake_run_rows(statement: str, params=None) -> list[dict[str, Any]]:
        captured["statement"] = statement
        captured["params"] = params
        return [{"id": 1}]

    monkeypatch.setattr(connector, "_run_rows", fake_run_rows)

    rows = await connector.sample_rows(Context("p", "r", "u"), "items", limit=500)

    assert rows == [{"id": 1}]
    assert captured["params"] == {"limit": 100}


def test_sql_dsn_security_rejects_non_loopback_disable_ssl() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))
    connector._dsn = "postgresql+asyncpg://prod.example/db?sslmode=disable"

    with pytest.raises(UnsupportedBackendError):
        connector._enforce_dsn_security()


def test_sql_detect_op_class_admin_branch() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    op_class = connector._detect_op_class("GRANT SELECT ON users TO reader")

    assert op_class is OpClass.ADMIN


def test_sql_build_query_rejects_template_braces() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    with pytest.raises(QueryFailure, match="f-string"):
        connector._build_query("SELECT * FROM {users}", None)


def test_register_sql_connectors_registers_factories() -> None:
    registry = BackendRegistry()
    policy = Policy(allow_reads=True)
    dsn_map = {
        "postgres": "postgresql+asyncpg://localhost/test",
        "mysql": "mysql+aiomysql://localhost/test",
        "sqlite": "sqlite+aiosqlite:///:memory:",
    }

    register_sql_connectors(registry, policy=policy, dsn_map=dsn_map)

    assert registry.get("postgres") is not None
    assert registry.get("mysql") is not None
    assert registry.get("sqlite") is not None


def test_unsupported_backend_version_raises() -> None:
    connector = DummySqlConnector(Policy(allow_reads=True))

    with pytest.raises(UnsupportedBackendError):
        if connector._parse_major("sqlite 2.9") < connector.minimum_supported_major:
            raise UnsupportedBackendError("unsupported")
