from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from mcpdb.db.policy import Policy
from mcpdb.db.sql.base import SqlConnector


class PostgresConnector(SqlConnector):
    backend = "postgres"
    minimum_supported_major = 13

    def __init__(self, *, dsn: str, policy: Policy, pool_size: int = 5) -> None:
        super().__init__(dsn=dsn, policy=policy, pool_size=pool_size)

    def _connect_args(self) -> dict[str, object]:
        return {"server_settings": {"application_name": "mcpdb"}}

    async def _check_server_version(self, connection: AsyncConnection) -> None:
        await super()._check_server_version(connection)
        timeout_ms = self._policy.query_timeout_ms
        await connection.execute(
            text("SET statement_timeout = :timeout_ms"),
            {"timeout_ms": timeout_ms},
        )
