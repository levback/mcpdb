from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mcpdb.db.base import Context, OperationResult
from mcpdb.db.policy import Policy
from mcpdb.db.sql.base import SqlConnector


class MysqlConnector(SqlConnector):
    backend = "mysql"
    minimum_supported_major = 8

    def __init__(self, *, dsn: str, policy: Policy, pool_size: int = 5) -> None:
        super().__init__(dsn=dsn, policy=policy, pool_size=pool_size)

    async def execute(
        self,
        context: Context,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> OperationResult:
        timeout_hint = f"/*+ MAX_EXECUTION_TIME({self._policy.query_timeout_ms}) */ "
        timed_statement = timeout_hint + statement
        return await super().execute(context, timed_statement, parameters)
