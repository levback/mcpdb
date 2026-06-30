filepath: phases/06-mcp-server-core.md
# Phase 06 — MCP Server Core, Tools & Resources

> **Pre-reqs:** phases 03–05 merged.

## §1. Objective
Expose database operations through the Model Context Protocol: `stdio` and `streamable-http` transports, a curated tool set, and resource URIs for schemas. Includes a typed `Context` passed to every tool.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/server/app.py` — `build_server(settings)`, transport wiring.
- `src/mcpdb/server/context.py` — `Context`, `RequestContext`.
- `src/mcpdb/server/tools.py` — `@mcp.tool` registrations for `db_query`, `db_introspect`, `db_ping`, `db_list_profiles`.
- `src/mcpdb/server/resources.py` — `db://` URI templates (`db://{profile}/tables`, `db://{profile}/schema/{table}`).
- `src/mcpdb/server/errors.py` — MCP-compliant error mapping.

Out of scope:
- OAuth, rate limiting, audit sink (phase 07).
- CLI wiring (phase 08).

## §3. Reference
DIRECTIVE.md §2 (mcp SDK, starlette, uvicorn), §5 A01/A04. Glossary: Tool, Resource, Context, Operation Class.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/server/__init__.py` | exports | 10 |
| `src/mcpdb/server/context.py` | `Context`, `RequestContext` (immutable per request) | 110 |
| `src/mcpdb/server/errors.py` | MCP error codes + mapping from internal exceptions | 90 |
| `src/mcpdb/server/resources.py` | resource templates + handlers | 120 |
| `src/mcpdb/server/tools.py` | tool registrations, parameter validation | 220 |
| `src/mcpdb/server/app.py` | `build_server`, transport selection, lifecycle | 180 |
| `tests/unit/server/test_context.py` | immutability, principal/correlation IDs | 70 |
| `tests/unit/server/test_errors.py` | mapping matrix for every internal exception | 120 |
| `tests/unit/server/test_resources.py` | URI parsing, missing profile, scope errors | 110 |
| `tests/unit/server/test_tools.py` | param validation, op-class checks, audit hooks | 200 |
| `tests/integration/server/test_stdio_transport.py` | end-to-end with `mcp.Client` over stdio | 180 |
| `tests/integration/server/test_http_transport.py` | end-to-end over streamable-http with `respx` | 200 |

## §5. Functional Requirements
1. `build_server(settings)` returns an `mcp.server.Server` ready for `run(transport=...)`.
2. `stdio` is the default when no transport is given; `http` requires explicit opt-in via settings + auth.
3. Tools: `db_query` (text+params for SQL, filter+projection for Mongo), `db_introspect` (target profile+scope), `db_ping` (latency), `db_list_profiles` (names + backends only, no creds).
4. Each tool enforces `OpClass` via injected `Policy`; results returned as structured dataclasses.
5. Resources are read-only; `db://{profile}/tables` lists table names + sizes; `db://{profile}/schema/{table}` returns JSON Schema.
6. All errors map to MCP error codes (`INVALID_PARAMS`, `UNAUTHORIZED`, `FORBIDDEN`, `INTERNAL`); no stack traces leaked.
7. `RequestContext` carries `correlation_id`, `principal`, `source_ip`, `user_agent`; immutable.

## §6. Test Plan
- `test_context_is_frozen`
- `test_context_correlation_id_propagates`
- `test_errors_policy_refused_maps_to_forbidden`
- `test_errors_unsupported_backend_maps_to_internal`
- `test_errors_invalid_params_carries_field_path`
- `test_resources_db_tables_lists_table_names`
- `test_resources_db_schema_returns_json_schema`
- `test_resources_invalid_profile_returns_not_found`
- `test_tools_db_query_sql_uses_bound_params`
- `test_tools_db_query_mongo_uses_filter_model`
- `test_tools_db_introspect_returns_columns`
- `test_tools_db_ping_measures_latency`
- `test_tools_db_list_profiles_does_not_leak_creds`
- `test_tools_db_query_read_only_denies_write` — OWASP A01
- `test_tools_db_query_admin_requires_admin_op_class`
- `test_tools_db_query_row_cap_applied`
- `test_tools_db_query_timeout_returned_as_error`
- `test_integration_stdio_lists_tools` — happy path with real client
- `test_integration_stdio_invokes_db_ping`
- `test_integration_http_starts_and_responds_health`
- `test_integration_http_rejects_request_without_auth_after_phase07` (skip if 07 not done)

## §7. Security Requirements
- A01: each tool checks OpClass; deny by default.
- A04: server holds no global mutable state; settings injected at build.
- A09: every tool invocation logs structured event with correlation_id; args redacted.

## §8. DoD
- [ ] `uv run mcpdb serve --transport stdio` accepts a client over stdio and `tools/list` returns the four tools.
- [ ] HTTP transport boots on `127.0.0.1:8765` and answers `/healthz` 200.
- [ ] Coverage ≥90% on `src/mcpdb/server/`.
- [ ] Bandit, mypy strict clean.

## §9. Anti-Patterns
- No `print()` in server code.
- No `try/except Exception` that swallows errors — log + re-raise.
- No direct import of `motor`/`asyncpg` here — go through `Connector`.
