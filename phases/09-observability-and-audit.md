filepath: phases/09-observability-and-audit.md
# Phase 09 — Observability & Audit (Structured Logging, Metrics, Tracing)

> **Pre-reqs:** phase 07 merged.

## §1. Objective
Make the server fully observable for production: structured JSON logs with secret redaction, Prometheus metrics, OpenTelemetry traces, and the audit log integration wired through every tool.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/observability/logging.py` — structlog config, redactor, contextvars bindings.
- `src/mcpdb/observability/metrics.py` — Prometheus registry, named metrics.
- `src/mcpdb/observability/tracing.py` — OTel setup, auto-instrumentation for `httpx`/`asyncpg`/`motor`.
- `src/mcpdb/observability/audit_integration.py` — glue that writes one audit entry per tool call with full `who/what/when/where`.

Out of scope:
- Grafana dashboard JSONs (separate repo, infra concern).
- Datadog/Splunk exporters (use OTLP only).

## §3. Reference
DIRECTIVE.md §2 (structlog, prometheus_client, opentelemetry). OWASP A09. NIST AU-2/AU-3/AU-9.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/observability/__init__.py` | exports | 10 |
| `src/mcpdb/observability/logging.py` | structlog + redactor + binders | 180 |
| `src/mcpdb/observability/metrics.py` | `Metrics` registry, HTTP middleware | 160 |
| `src/mcpdb/observability/tracing.py` | OTel SDK setup | 140 |
| `src/mcpdb/observability/audit_integration.py` | middleware that emits audit per call | 120 |
| `tests/unit/observability/test_logging.py` | redaction corpus, JSON shape | 150 |
| `tests/unit/observability/test_metrics.py` | counter/histogram increments | 120 |
| `tests/unit/observability/test_tracing.py` | span lifecycle, baggage | 120 |
| `tests/security/test_log_injection_a09.py` | log forging attempts | 100 |
| `tests/integration/observability/test_otel_otlp.py` | OTLP exporter to local collector | 150 |

## §5. Functional Requirements
1. structlog configured for JSON to stdout; key order stable; ISO-8601 timestamps UTC.
2. Redactor uses an extensible list of regexes + key allow-list; secret fields logged as `[REDACTED]`.
3. Metrics: `mcpdb_requests_total{tool,op_class,outcome}`, `mcpdb_request_duration_seconds` (histogram), `mcpdb_rows_returned_total`, `mcpdb_query_timeouts_total`, `mcpdb_policy_denials_total`.
4. `/metrics` endpoint mounted on HTTP transport when enabled.
5. OTel: batch span processor, OTLP exporter to `OTEL_EXPORTER_OTLP_ENDPOINT`; default off.
6. Per tool call: one info log + one audit entry + spans (`server.request`, `db.execute`); correlation_id propagated via `contextvars`.

## §6. Test Plan
- `test_logging_emits_stable_json`
- `test_logging_redacts_password_field`
- `test_logging_redacts_authorization_header`
- `test_logging_redacts_connection_string`
- `test_logging_unicode_keys_not_mangled`
- `test_metrics_request_counter_increments`
- `test_metrics_histogram_records_latency`
- `test_metrics_endpoint_serves_text_format`
- `test_tracing_span_starts_and_ends`
- `test_tracing_context_propagates_to_db`
- `test_audit_integration_writes_one_entry_per_call`
- `test_audit_integration_includes_correlation_id`
- `test_security_log_injection_newline_blocked`
- `test_integration_otel_export_to_collector` (skippable if collector absent)

## §7. Security Requirements
- A09: forbid `\n`, `\r`, control chars in log values; redact secrets; log forging tests must pass.
- NIST AU-9: audit entries tamper-evident (HMAC chain, already in phase 07).
- NIST SI-10: input validated before formatting into log lines.

## §8. DoD
- [ ] All §6 tests pass.
- [ ] `/metrics` text exposition is valid (Prometheus parser test).
- [ ] Coverage ≥90% on `src/mcpdb/observability/`.

## §9. Anti-Patterns
- No `logging.getLogger().info("..." % user_input)` — use structured fields only.
- No global OTel tracer — pass through DI where useful, single setup in app factory.
- No metrics without label bounds — cardinality audit before release.
