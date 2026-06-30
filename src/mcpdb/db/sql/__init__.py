from mcpdb.db.policy import Policy
from mcpdb.db.registry import BackendRegistry
from mcpdb.db.sql.base import SqlConnector, SqlQuery, UnsupportedBackendError
from mcpdb.db.sql.mysql import MysqlConnector
from mcpdb.db.sql.postgres import PostgresConnector
from mcpdb.db.sql.sqlite import SqliteConnector


def register_sql_connectors(
    registry: BackendRegistry,
    *,
    policy: Policy,
    dsn_map: dict[str, str],
) -> None:
    registry.register(
        "postgres",
        lambda: PostgresConnector(dsn=dsn_map["postgres"], policy=policy),
    )
    registry.register(
        "mysql",
        lambda: MysqlConnector(dsn=dsn_map["mysql"], policy=policy),
    )
    registry.register(
        "sqlite",
        lambda: SqliteConnector(dsn=dsn_map["sqlite"], policy=policy),
    )


__all__ = [
    "MysqlConnector",
    "PostgresConnector",
    "SqlConnector",
    "SqlQuery",
    "SqliteConnector",
    "UnsupportedBackendError",
    "register_sql_connectors",
]
