filepath: phases/04-sql-connectors.md
# Phase 04 — SQL Connectors (PostgreSQL, MySQL, SQLite)

> **Pre-reqs:** phase 03 merged.

## §1. Objective
Implement `Connector` for the three SQL backends using SQLAlchemy 2.0 Core with async drivers. All queries must go through bound parameters — no string concatenation, ever.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/db/sql/base.py` — shared SQLAlchemy-backed base class.
- `src/mcpdb/db/sql/postgres.py`, `mysql.py`, `sqlite.py` — thin per-backend subclasses.
- `src/mcpdb/db/sql/dialect.py` — safe identifier quoting, type map.
- Param-binding query builder (text + params, never f-string).
- Introspection: list_schemas, list_tables, describe_table, list_indexes, sample_rows.

Out of scope:
- MongoDB (phase 05), MCP wrappers (phase 06), auth (phase 07).

## §3. Reference
DIRECTIVE.md §2 (SQLAlchemy, async drivers), §5 A03 Injection. Glossary: Connector, Policy, OpClass.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/db/sql/__init__.py` | public exports, registration helpers | 25 |
| `src/mcpdb/db/sql/base.py` | `SqlConnector`, lifecycle, transaction ctx | 220 |
| `src/mcpdb/db/sql/dialect.py` | identifier validation, type adapters | 80 |
| `src/mcpdb/db/sql/postgres.py` | `PostgresConnector(asyncpg)` | 70 |
| `src/mcpdb/db/sql/mysql.py` | `MysqlConnector(aiomysql)` | 70 |
| `src/mcpdb/db/sql/sqlite.py` | `SqliteConnector(aiosqlite)` | 70 |
| `tests/unit/db/sql/test_dialect.py` | identifier allow-list, injection attempts | 100 |
| `tests/unit/db/sql/test_sql_base.py` | policy enforcement, timeout, row-cap | 180 |
| `tests/integration/db/sql/test_postgres.py` | real `pytest-postgresql` | 150 |
| `tests/integration/db/sql/test_mysql.py` | real `pytest-mysql` | 150 |
| `tests/integration/db/sql/test_sqlite.py` | real `aiosqlite` tempfile | 120 |
| `tests/security/test_sql_a03.py` | parametrized SQL injection corpus | 200 |

## §5. Functional Requirements
1. `execute(query: SqlQuery) -> OperationResult`: query text + bound params (`Mapping[str, Any]`). Refuses anything built via f-string detection (logged).
2. `introspect(target) -> SchemaInfo`: tables, columns (name, type, null, default), indexes, FKs.
3. Connection pool: 1–10, pre-ping enabled, recycle 1800s.
4. Apply `Policy.query_timeout_ms` via `statement_timeout` (pg) / `MAX_EXECUTION_TIME` hint (mysql) / per-statement asyncio timeout (sqlite).
5. Identify via `ServerVersion`; refuse unsupported majors (mysql < 8, pg < 13, sqlite < 3.40) — emit `UnsupportedBackendError`.
6. `transaction()` async ctx applies BEGIN/COMMIT/ROLLBACK; `PolicyRefused` rolls back.

## §6. Test Plan
- `test_dialect_identifier_must_match_safe_regex`
- `test_dialect_identifier_rejects_embedded_quote`
- `test_sql_execute_uses_bound_params` — assertion on `cursor.execute` call args (mock)
- `test_sql_execute_injection_attempt_blocked` — corpus from OWASP A03
- `test_sql_introspect_returns_expected_columns`
- `test_sql_introspect_lists_schemas` (pg only)
- `test_sql_pool_pre_ping_recovers_from_dead_socket`
- `test_sql_query_timeout_fires_and_cancels`
- `test_sql_row_cap_truncates_with_warning`
- `test_sql_read_only_policy_denies_insert`
- `test_sql_transaction_rollback_on_policy_refused`
- `test_sql_postgres_integration_round_trip`
- `test_sql_mysql_integration_round_trip`
- `test_sql_sqlite_integration_round_trip`
- `test_unsupported_backend_version_raises`

## §7. Security Requirements
- A03 Injection: corpus test in `test_security_a03.py` must include `' OR '1'='1`, `'; DROP`, UNICODE smuggling, second-order payloads.
- A05: refuse connection strings with `sslmode=disable` to non-loopback.
- NIST AU-3: every `execute` logs query fingerprint (SHA-256 of canonicalized text+params), never the value.

## §8. DoD
- [ ] All three SQL backends pass integration tests in CI via service containers.
- [ ] `bandit -r src/mcpdb/db/sql` clean.
- [ ] OWASP A03 corpus test passes 100 payloads × 3 backends.
- [ ] Coverage ≥90% on `src/mcpdb/db/sql/`.

## §9. Anti-Patterns
- No string concatenation in SQL anywhere — grep gate in CI: `rg "f\".*SELECT.*\"" src/`.
- No `text(f"...")` from user input.
- No raw `cursor.execute("...", ())` — must use `executemany` or bound param dict.
