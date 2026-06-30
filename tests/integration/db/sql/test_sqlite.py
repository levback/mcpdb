from __future__ import annotations

from pathlib import Path

import pytest

from mcpdb.db.base import Context
from mcpdb.db.policy import Policy
from mcpdb.db.sql.sqlite import SqliteConnector


@pytest.mark.asyncio
async def test_sql_sqlite_integration_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "integration.sqlite"
    dsn = f"sqlite+aiosqlite:///{db_path}"
    connector = SqliteConnector(dsn=dsn, policy=Policy(allow_reads=True, allow_writes=True))
    context = Context(profile="sqlite", request_id="it-1", principal="integration")

    await connector.connect(context)
    await connector.execute(context, "CREATE TABLE items(id INTEGER PRIMARY KEY, name TEXT)")
    await connector.execute(context, "INSERT INTO items(name) VALUES (:name)", {"name": "alpha"})
    result = await connector.execute(context, "SELECT name FROM items WHERE id = :id", {"id": 1})
    await connector.close(context)

    assert result.row_count == 1
    assert result.rows[0]["name"] == "alpha"
