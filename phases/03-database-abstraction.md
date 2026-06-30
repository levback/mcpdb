filepath: phases/03-database-abstraction.md
# Phase 03 — Database Abstraction Layer

> **Pre-reqs:** phase 02 merged.

## §1. Objective
Define a backend-agnostic `Connector` Protocol, a `Policy` decision object, and a `BackendRegistry` that produces connector instances by backend key. No real DB drivers yet — only the contracts and fakes for tests.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/db/base.py` — `Connector` Protocol, `OperationResult`, exceptions.
- `src/mcpdb/db/policy.py` — `Policy`, `OpClass`, decision logic.
- `src/mcpdb/db/registry.py` — `BackendRegistry` with thread-safe `register/get`.
- `src/mcpdb/db/fake.py` — `FakeConnector` for unit tests.
- Health-check contract: `ping() -> float` (latency ms).

Out of scope:
- Real DB drivers (phase 04 SQL, phase 05 NoSQL).
- MCP tool implementation (phase 06).
- Authn/authz (phase 07).

## §3. Reference
DIRECTIVE.md §5 (A01, A04). Glossary: Connector, Policy, Operation Class, Cap.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/db/__init__.py` | public re-exports | 12 |
| `src/mcpdb/db/base.py` | Protocol, dataclasses, exception hierarchy | 130 |
| `src/mcpdb/db/policy.py` | `Policy`, `OpClass`, decisions, caps | 150 |
| `src/mcpdb/db/registry.py` | `BackendRegistry`, `_check` decorator | 80 |
| `src/mcpdb/db/fake.py` | `FakeConnector`, programmable failure mode | 90 |
| `tests/unit/db/test_base.py` | protocol structural checks | 60 |
| `tests/unit/db/test_policy.py` | allow/deny matrix, cap math | 180 |
| `tests/unit/db/test_registry.py` | register/get/dup/thread-safety | 100 |
| `tests/unit/db/test_fake.py` | failure injection, latency modeling | 70 |
| `tests/properties/test_policy_properties.py` | caps monotonic, deny idempotent | 60 |

## §5. Functional Requirements
1. `Connector` Protocol methods: `connect`, `close`, `ping`, `execute`, `introspect`, `transaction`. All async.
2. `OpClass` is `Enum` of READ, WRITE, ADMIN. `Policy.decide(op_class) -> Decision`.
3. `Policy` has `query_timeout_ms`, `max_rows`, `max_payload_bytes`, `allow_writes`, `allow_admin`, `allowlist_tables` (optional tuple).
4. `Decision` carries `allowed: bool`, `reason: str`, `adjusted_cap: Cap | None`.
5. `BackendRegistry.register(backend, factory_fn)` and `BackendRegistry.get(backend) -> ConnectorFactory` with `KeyError` and `RegistryError`.
6. `PolicyRefused` is a dedicated exception; HTTP mapping (429/403) handled later.
7. `FakeConnector` supports `set_failure(mode, n_calls)` for chaos tests in phase 10.

## §6. Test Plan
- `test_connector_protocol_satisfied_by_fake`
- `test_connector_protocol_unsatisfied_by_minimal_class`
- `test_policy_read_only_denies_write_with_clear_reason` — OWASP A01
- `test_policy_allowlist_blocks_unlisted_table`
- `test_policy_max_rows_caps_result_size`
- `test_policy_timeout_adjusted_to_min_of_policy_and_request`
- `test_policy_admin_requires_explicit_opt_in`
- `test_policy_decision_is_pure` — same input → same output
- `test_registry_register_then_get`
- `test_registry_duplicate_backend_raises`
- `test_registry_get_unknown_raises`
- `test_registry_concurrent_register_is_safe` — threads
- `test_fake_records_all_calls_with_args_kwargs`
- `test_fake_injects_transient_failure_then_recovers`
- `test_fake_ping_returns_configured_latency_ms`
- `test_properties_caps_monotonic_when_policy_intensified`
- `test_properties_deny_decision_is_idempotent`

## §7. Security Requirements
- A01: default policy denies everything; explicit ops only.
- A04: connector takes a `Context` (profile, request_id, principal); no globals.
- All decisions audit-logged (placeholder log call, real sink in phase 09).

## §8. DoD
- [ ] Protocols are `runtime_checkable`; `isinstance` works for `Connector`.
- [ ] `BackendRegistry` covered with concurrent test (≥1000 ops).
- [ ] mypy strict on `db/`; bandit clean.
- [ ] Coverage ≥90% on `src/mcpdb/db/`.

## §9. Anti-Patterns
- No `class Connector(ABC)` mixed with `Protocol` — choose `Protocol` only.
- No mutable dataclass defaults; no `__hash__` overrides without thought.
- No `singledispatch` (we want explicit registration).
