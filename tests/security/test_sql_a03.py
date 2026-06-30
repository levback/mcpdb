from __future__ import annotations

import pytest

from mcpdb.db.base import Context, QueryFailure
from mcpdb.db.policy import Policy
from mcpdb.db.sql.mysql import MysqlConnector
from mcpdb.db.sql.postgres import PostgresConnector
from mcpdb.db.sql.sqlite import SqliteConnector


class MemorySqliteConnector(SqliteConnector):
    def __init__(self) -> None:
        super().__init__(dsn="sqlite+aiosqlite:///:memory:", policy=Policy(allow_reads=True))


def build_payloads() -> list[str]:
    seeds = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "admin'--",
        "admin' /*",
        "\uff07 OR \uff071\uff07=\uff071",
        "1; SELECT pg_sleep(1)",
        "1; WAITFOR DELAY '00:00:01'",
        "1 UNION SELECT password FROM users",
        "x' OR 1=1 --",
        "xp_cmdshell('dir')",
    ]
    payloads: list[str] = []
    for index in range(10):
        for seed in seeds:
            payloads.append(f"{seed} /*{index}*/")
    return payloads


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "connector_cls",
    [PostgresConnector, MysqlConnector, MemorySqliteConnector],
)
@pytest.mark.parametrize("payload", build_payloads())
async def test_sql_execute_injection_attempt_blocked(payload: str, connector_cls) -> None:
    if connector_cls is PostgresConnector:
        connector = connector_cls(
            dsn="postgresql+asyncpg://localhost/test",
            policy=Policy(allow_reads=True),
        )
    elif connector_cls is MysqlConnector:
        connector = connector_cls(
            dsn="mysql+aiomysql://localhost/test",
            policy=Policy(allow_reads=True),
        )
    else:
        connector = connector_cls()

    with pytest.raises(QueryFailure):
        await connector.execute(
            Context(profile="sec", request_id="a03", principal="security"),
            f"SELECT * FROM users WHERE username = '{payload}'",
        )
