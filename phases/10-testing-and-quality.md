filepath: phases/10-testing-and-quality.md
# Phase 10 — Testing & Quality (Property, Fuzz, Chaos, Mutation)

> **Pre-reqs:** phases 04–09 merged.

## §1. Objective
Harden the test suite beyond example-based: property-based tests across all inputs, fuzzing the JSON-RPC boundary, chaos on the DB layer, and mutation testing to prove the suite actually catches bugs.

## §2. SCOPE BOUNDARY
In scope:
- `tests/properties/` — Hypothesis strategies for `MongoFilter`, `SqlQuery`, `Policy`, `Config`.
- `tests/fuzz/` — `atheris` (libFuzzer) harness for the JSON-RPC parser and config loader.
- `tests/chaos/` — fault injection across `Connector` boundaries using `FakeConnector`.
- `tests/mutation/` — `mutmut` config and run docs; CI compares kill ratio against threshold (≥75%).

Out of scope:
- Performance benchmarking (phase 11 as docs only).
- Hardware fault injection (kernel-level chaos).

## §3. Reference
DIRECTIVE.md §2 (hypothesis, atheris, mutmut). OWASP A04 design robustness. NIST SP 800-53 SA-11 (testing).

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `tests/properties/test_mongo_filter_props.py` | round-trip + invariants | 120 |
| `tests/properties/test_sql_query_props.py` | bindings cannot be coerced to SQL | 120 |
| `tests/properties/test_policy_props.py` | caps monotonic; deny idempotent | 90 |
| `tests/properties/test_config_props.py` | configs round-trip after dump/load | 110 |
| `tests/fuzz/fuzz_jsonrpc.py` | atheris harness for MCP JSON-RPC parser | 100 |
| `tests/fuzz/fuzz_config.py` | atheris harness for YAML/JSON config loader | 100 |
| `tests/chaos/test_connector_chaos.py` | transient failure, timeout, slow drain | 200 |
| `tests/chaos/test_server_chaos.py` | mid-call drops, partial responses | 180 |
| `tests/mutation/mutmut.toml` | config | 20 |
| `tests/mutation/README.md` | how to run + interpret | 40 |
| `scripts/quality.sh` | runs fuzz (short), property, mutation (incremental) | 40 |

## §5. Functional Requirements
1. Property tests generate **≥1000** cases per `@given`.
2. Fuzz runs **≥30 seconds** in CI on the `fuzz_*` harnesses with at least one crashing input corpus checked in.
3. Chaos suite covers: connector raises mid-iteration; timeout fires under load; partial bytes read.
4. Mutation suite: `mutmut run` finishes in <10 min on a warm cache; ≥75% killed.

## §6. Test Plan
- `test_mongo_filter_round_trip_via_motor_translator`
- `test_mongo_filter_rejects_unknown_op_invariant`
- `test_sql_query_binds_never_string_concat_invariant`
- `test_policy_caps_monotonic_under_intensify`
- `test_config_dump_then_load_equals_original`
- `test_fuzz_jsonrpc_no_unhandled_exception` (with seeded corpus)
- `test_fuzz_config_no_unhandled_exception`
- `test_chaos_transient_failure_does_not_corrupt_state`
- `test_chaos_timeout_is_observable_and_cancellable`
- `test_chaos_partial_bytes_do_not_panic_parser`
- `test_mutation_kill_ratio_above_threshold` — non-flaky gate

## §7. Security Requirements
- A04: invariant-based property tests act as design assertions; failures must surface design flaws.
- NIST SA-11: independent test suite documented + reproducible.

## §8. DoD
- [ ] `scripts/quality.sh fuzz` runs 60s locally and finds no new crashes.
- [ ] `mutmut run` reports ≥75% killed on `src/mcpdb/db/` + `src/mcpdb/server/`.
- [ ] Fuzz crash corpus is empty after run; new crashes immediately fail CI.

## §9. Anti-Patterns
- No `hypothesis.seed(0)` in production paths (CI only).
- No disabling slow tests via `pytest.mark.skip` — mark as `@pytest.mark.slow` and run nightly.
- No committing fuzzer corpora larger than 256 KB.
