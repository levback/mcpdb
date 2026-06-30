from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import ResourceClosedError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from mcpdb.db.base import Connector, Context, OperationResult, PolicyRefused, QueryFailure
from mcpdb.db.policy import OpClass, Policy
from mcpdb.db.sql.dialect import quote_table

LOGGER = logging.getLogger(__name__)
INJECTION_PATTERNS = [
    re.compile(r"'\s*or\s*'1'\s*=\s*'1", re.IGNORECASE),
    re.compile(r";\s*drop\s+", re.IGNORECASE),
    re.compile(r"--"),
    re.compile(r"/\*.*\*/", re.IGNORECASE),
    re.compile(r"xp_cmdshell", re.IGNORECASE),
    re.compile(r"\uff07"),
]


class UnsupportedBackendError(QueryFailure):
    """Raised when backend version is unsupported."""


@dataclass(frozen=True)
class SqlQuery:
    statement: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class BufferedResult:
    rows: list[dict[str, Any]]
    row_count: int


class SqlConnector(Connector):
    backend: str = "sql"
    minimum_supported_major: int = 0

    def __init__(
        self,
        *,
        dsn: str,
        policy: Policy,
        pool_size: int = 5,
        max_overflow: int = 5,
        connect_timeout_s: float = 5.0,
    ) -> None:
        self._dsn = dsn
        self._policy = policy
        self._pool_size = max(1, min(pool_size, 10))
        self._max_overflow = max(0, min(max_overflow, 10))
        self._connect_timeout_s = connect_timeout_s
        self._engine: AsyncEngine | None = None

    async def connect(self, context: Context) -> None:
        self._enforce_dsn_security()
        self._engine = create_async_engine(
            self._dsn,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args=self._connect_args(),
        )
        async with self._engine.connect() as connection:
            await self._check_server_version(connection)

    async def close(self, context: Context) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

    async def ping(self, context: Context) -> float:
        started = perf_counter()
        await self._run_scalar("SELECT 1")
        return (perf_counter() - started) * 1000

    async def execute(
        self,
        context: Context,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> OperationResult:
        op_class = self._detect_op_class(statement)
        decision = self._policy.decide(op_class)
        if not decision.allowed:
            raise PolicyRefused(decision.reason)  # OWASP A01: deny by policy decision

        sql_query = self._build_query(statement, parameters)
        if self._looks_like_injection(sql_query.statement):
            raise QueryFailure("Potential SQL injection payload detected")  # OWASP A03

        fingerprint = self._fingerprint(sql_query)
        LOGGER.info("sql_execute fingerprint=%s", fingerprint)  # NIST AU-3: fingerprint only

        started = perf_counter()
        result = await self._run_with_timeout(
            self._execute_query(sql_query),
            self._effective_timeout_ms(),
        )
        latency_ms = (perf_counter() - started) * 1000

        rows, row_count = self._extract_rows(result)
        adjusted_cap = (
            decision.adjusted_cap if decision.adjusted_cap is not None else self._policy.base_cap()
        )
        truncated_rows = rows[: adjusted_cap.max_rows]
        payload_bytes = len(json.dumps(truncated_rows, default=str))
        return OperationResult(
            rows=tuple(truncated_rows),
            row_count=row_count,
            payload_bytes=payload_bytes,
            latency_ms=latency_ms,
            truncated=row_count > len(truncated_rows),
        )

    async def introspect(self, context: Context, target: str | None = None) -> OperationResult:
        if target is None:
            tables = await self.list_tables(context)
            return OperationResult(rows=tuple(tables), row_count=len(tables), payload_bytes=256)

        columns = await self.describe_table(context, target)
        indexes = await self.list_indexes(context, target)
        rows = tuple(columns + indexes)
        return OperationResult(rows=rows, row_count=len(rows), payload_bytes=512)

    async def transaction(self, context: Context) -> None:
        async with self.transaction_context(context):
            return None

    @asynccontextmanager
    async def transaction_context(
        self,
        context: Context,
    ) -> AsyncIterator[AsyncConnection]:
        connection = await self._connection()
        transaction = await connection.begin()
        try:
            yield connection
            await transaction.commit()
        except PolicyRefused:
            await transaction.rollback()
            raise
        except Exception:
            await transaction.rollback()
            raise

    async def list_schemas(self, context: Context) -> list[dict[str, Any]]:
        if self.backend == "sqlite":
            return [{"schema": "main"}]
        rows = await self._run_rows(
            "SELECT schema_name AS schema FROM information_schema.schemata ORDER BY schema_name"
        )
        return [{"schema": row.get("schema")} for row in rows]

    async def list_tables(self, context: Context) -> list[dict[str, Any]]:
        if self.backend == "sqlite":
            rows = await self._run_rows(
                "SELECT name AS table_name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
            return [{"table": row.get("table_name")} for row in rows]

        rows = await self._run_rows(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema') "
            "ORDER BY table_name"
        )
        return [{"table": row.get("table_name")} for row in rows]

    async def describe_table(self, context: Context, table: str) -> list[dict[str, Any]]:
        table_name = table.split(".")[-1]
        if self.backend == "sqlite":
            quoted = quote_table(self.backend, table_name)
            rows = await self._run_rows(f"PRAGMA table_info({quoted})")
            return [
                {
                    "column": row.get("name"),
                    "type": row.get("type"),
                    "nullable": row.get("notnull") == 0,
                    "default": row.get("dflt_value"),
                }
                for row in rows
            ]

        rows = await self._run_rows(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = :table_name "
            "ORDER BY ordinal_position",
            {"table_name": table_name},
        )
        return [
            {
                "column": row.get("column_name"),
                "type": row.get("data_type"),
                "nullable": str(row.get("is_nullable", "")).upper() == "YES",
                "default": row.get("column_default"),
            }
            for row in rows
        ]

    async def list_indexes(self, context: Context, table: str) -> list[dict[str, Any]]:
        table_name = table.split(".")[-1]
        if self.backend == "sqlite":
            rows = await self._run_rows(
                f"PRAGMA index_list({quote_table(self.backend, table_name)})"
            )
            return [{"index": row.get("name"), "unique": bool(row.get("unique"))} for row in rows]

        rows = await self._run_rows(
            "SELECT indexname AS index_name FROM pg_indexes WHERE tablename = :table_name",
            {"table_name": table_name},
        )
        return [{"index": row.get("index_name"), "unique": None} for row in rows]

    async def sample_rows(
        self,
        context: Context,
        table: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        quoted = quote_table(self.backend, table)
        return await self._run_rows(f"SELECT * FROM {quoted} LIMIT :limit", {"limit": safe_limit})

    def _build_query(
        self,
        statement: str,
        parameters: Mapping[str, Any] | None,
    ) -> SqlQuery:
        params = dict(parameters or {})
        if "{" in statement or "}" in statement:
            raise QueryFailure("Potential f-string template detected")
        return SqlQuery(statement=statement, parameters=params)

    def _detect_op_class(self, statement: str) -> OpClass:
        normalized = statement.lstrip().lower()
        if normalized.startswith(("insert", "update", "delete", "create", "drop", "alter")):
            return OpClass.WRITE
        if normalized.startswith(("grant", "revoke", "vacuum", "analyze", "set ")):
            return OpClass.ADMIN
        return OpClass.READ

    def _looks_like_injection(self, statement: str) -> bool:
        return any(pattern.search(statement) is not None for pattern in INJECTION_PATTERNS)

    def _fingerprint(self, query: SqlQuery) -> str:
        canonical = query.statement.strip() + "|" + ",".join(sorted(query.parameters.keys()))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _effective_timeout_ms(self) -> int:
        return self._policy.query_timeout_ms

    def _enforce_dsn_security(self) -> None:
        if (
            "sslmode=disable" in self._dsn
            and not self._dsn.startswith("sqlite")
            and "localhost" not in self._dsn
            and "127.0.0.1" not in self._dsn
        ):
            raise UnsupportedBackendError(
                "Refusing non-loopback DSN with sslmode=disable"
            )  # OWASP A05

    def _connect_args(self) -> dict[str, Any]:
        return {"timeout": self._connect_timeout_s}

    async def _check_server_version(self, connection: AsyncConnection) -> None:
        version_text = await self._server_version(connection)
        major = self._parse_major(version_text)
        if major < self.minimum_supported_major:
            raise UnsupportedBackendError(
                f"{self.backend} major version {major} is unsupported "
                f"(need >= {self.minimum_supported_major})"
            )

    async def _server_version(self, connection: AsyncConnection) -> str:
        if self.backend == "sqlite":
            value = await connection.scalar(text("select sqlite_version()"))
            return str(value)
        value = await connection.scalar(text("select version()"))
        return str(value)

    def _parse_major(self, version_text: str) -> int:
        match = re.search(r"(\d+)\.", version_text)
        if match is None:
            return 0
        return int(match.group(1))

    async def _connection(self) -> AsyncConnection:
        if self._engine is None:
            raise QueryFailure("connector is not connected")
        return await self._engine.connect()

    async def _execute_query(self, query: SqlQuery) -> BufferedResult:
        connection = await self._connection()
        try:
            statement = text(query.statement)
            result = await connection.execute(
                statement,
                query.parameters,
            )  # OWASP A03: bound parameters only
            rows, row_count = self._extract_rows(result)
            await connection.commit()
            return BufferedResult(rows=rows, row_count=row_count)
        finally:
            await connection.close()

    async def _run_with_timeout(self, awaitable: Any, timeout_ms: int) -> Any:
        try:
            return await asyncio.wait_for(awaitable, timeout=timeout_ms / 1000)
        except TimeoutError as error:
            raise QueryFailure("Query execution timed out") from error

    def _extract_rows(
        self,
        result: BufferedResult | CursorResult[Any] | Any,
    ) -> tuple[list[dict[str, Any]], int]:
        if isinstance(result, BufferedResult):
            return list(result.rows), result.row_count

        try:
            mappings = [dict(row) for row in result.mappings().all()]
            return mappings, len(mappings)
        except ResourceClosedError:
            row_count = (
                result.rowcount if result.rowcount is not None and result.rowcount >= 0 else 0
            )
            return [], row_count

    async def _run_rows(
        self,
        statement: str,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        result = await self._execute_query(
            SqlQuery(statement=statement, parameters=dict(params or {}))
        )
        rows, _ = self._extract_rows(result)
        return rows

    async def _run_scalar(self, statement: str) -> Any:
        connection = await self._connection()
        try:
            return await connection.scalar(text(statement))
        finally:
            await connection.close()
