filepath: phases/05-nosql-connectors.md
# Phase 05 — NoSQL Connectors (MongoDB)

> **Pre-reqs:** phase 03 merged (phase 04 recommended but not blocking).

## §1. Objective
Implement `Connector` for MongoDB 7 using Motor. Build queries from a typed `MongoFilter` model with an operator allow-list; reject `$where`, `$function`, `mapReduce`, and JS evaluation operators by default.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/db/nosql/mongo.py` — `MongoConnector`.
- `src/mcpdb/db/nosql/query.py` — `MongoFilter`, `MongoPipeline`, builders, validation.
- Introspection: list databases, list collections, sample schemas, indexes, stats.

Out of scope:
- Atlas Vector Search, change streams, transactions (post-1.0).
- HTTP MCP transports (phase 06).

## §3. Reference
DIRECTIVE.md §2 (motor), §5 A03. Glossary: Policy, Operation Class.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/db/nosql/__init__.py` | exports | 10 |
| `src/mcpdb/db/nosql/query.py` | `MongoFilter`, validators, op allow-list | 160 |
| `src/mcpdb/db/nosql/mongo.py` | `MongoConnector` (Motor) | 220 |
| `tests/unit/db/nosql/test_query.py` | operator allow-list, type coercion | 150 |
| `tests/integration/db/nosql/test_mongo.py` | real `pytest-mongodb` | 150 |
| `tests/security/test_mongo_a03.py` | `$where`, `$function`, `mapReduce` JS blocked | 130 |

## §5. Functional Requirements
1. `MongoFilter` is a pydantic model: `{"field": {"$eq": value}, "x": {"$in": [...]}}`.
2. Operators allowed: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`, `$and`, `$or`, `$exists`, `$type`, `$all`. All others → `MongoFilterError`.
3. `$regex` allowed **only** when `config.regex_enabled=True` AND pattern compiled from a literal string (not user concatenation) AND timeout set.
4. `find(filter, projection, limit)` returns dataclass rows; projection validated.
5. `aggregate(pipeline)` — pipeline operators allow-list; reject `$out`, `$merge`, `$lookup` to collections outside profile scope.
6. Introspection via `list_collection_names`, `index_information`, `estimated_document_count`.
7. `serverStatus` requires `OpClass.ADMIN`.

## §6. Test Plan
- `test_filter_eq_ne_gt_translates_to_motor`
- `test_filter_$where_is_rejected_with_clear_error` — OWASP A03
- `test_filter_$function_is_rejected` — OWASP A03
- `test_filter_$regex_rejected_when_disabled`
- `test_filter_$regex_timeout_set_when_enabled`
- `test_filter_in_nin_type_validated`
- `test_aggregate_$out_rejected`
- `test_aggregate_$lookup_within_same_db_allowed`
- `test_aggregate_$lookup_cross_db_rejected`
- `test_introspect_lists_collections`
- `test_introspect_returns_sample_schema`
- `test_introspect_server_status_requires_admin`
- `test_policy_read_only_blocks_insert_one`
- `test_mongo_integration_insert_find`
- `test_mongo_integration_aggregation_pipeline`

## §7. Security Requirements
- A03: JS operators denied by default; `$lookup` scope-checked.
- A05: refuse `directConnection=true` to non-loopback (forces TLS).
- A10 SSRF: if Mongo URL has `+srv`, resolve once at config load.
- NIST AU-3: log query fingerprint (canonical JSON, stable key order).

## §8. DoD
- [ ] `bandit` clean; mypy strict clean on `nosql/`.
- [ ] OWASP A03 corpus test for Mongo includes `{"$where": "..."}`, JS injection.
- [ ] Integration test green on `mongo:7` container.
- [ ] Coverage ≥90% on `src/mcpdb/db/nosql/`.

## §9. Anti-Patterns
- No `client[db].command("eval", ...)` anywhere.
- No `bson.decode` on untrusted raw bytes (validate via pydantic first).
- No `update_many({}, user_dict)` — must use `$set` only with schema-validated dict.
