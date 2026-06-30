from __future__ import annotations

from mcpdb.db.policy import Policy
from mcpdb.db.sql.base import SqlConnector


class SqliteConnector(SqlConnector):
    backend = "sqlite"
    minimum_supported_major = 3

    def __init__(self, *, dsn: str, policy: Policy, pool_size: int = 1) -> None:
        super().__init__(dsn=dsn, policy=policy, pool_size=pool_size, max_overflow=0)
