from __future__ import annotations

import os

import pytest

from mcpdb.db.base import Context
from mcpdb.db.policy import Policy
from mcpdb.db.sql.mysql import MysqlConnector


@pytest.mark.asyncio
async def test_sql_mysql_integration_round_trip() -> None:
    dsn = os.getenv("MCPDB_TEST_MYSQL_DSN")
    if not dsn:
        pytest.skip("MCPDB_TEST_MYSQL_DSN is not configured")

    connector = MysqlConnector(dsn=dsn, policy=Policy(allow_reads=True, allow_writes=True))
    context = Context(profile="mysql", request_id="it-mysql", principal="integration")

    await connector.connect(context)
    await connector.execute(context, "CREATE TEMPORARY TABLE mcpdb_items(id INT, name VARCHAR(64))")
    await connector.execute(
        context,
        "INSERT INTO mcpdb_items(id, name) VALUES (:id, :name)",
        {"id": 1, "name": "alpha"},
    )
    result = await connector.execute(
        context,
        "SELECT name FROM mcpdb_items WHERE id = :id",
        {"id": 1},
    )
    await connector.close(context)

    assert result.row_count == 1
    assert result.rows[0]["name"] == "alpha"
