from __future__ import annotations

import os

import pytest

from mcpdb.db.base import Context
from mcpdb.db.policy import Policy
from mcpdb.db.sql.postgres import PostgresConnector


@pytest.mark.asyncio
async def test_sql_postgres_integration_round_trip() -> None:
    dsn = os.getenv("MCPDB_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("MCPDB_TEST_POSTGRES_DSN is not configured")

    connector = PostgresConnector(dsn=dsn, policy=Policy(allow_reads=True, allow_writes=True))
    context = Context(profile="postgres", request_id="it-pg", principal="integration")

    await connector.connect(context)
    await connector.execute(context, "CREATE TEMP TABLE mcpdb_items(id INT, name TEXT)")
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
