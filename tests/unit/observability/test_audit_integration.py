from __future__ import annotations

import json
import time
from pathlib import Path

from mcpdb.observability.audit_integration import (
    AuditMiddleware,
    ToolInvocationRecord,
    _NullSink,
    build_audit_middleware,
    make_invocation_record,
)
from mcpdb.security.audit import AuditEntry, AuditSink, HMACChainSink


class CaptureSink(AuditSink):
    """Test helper that records every AuditEntry without hashing."""

    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def write(self, entry: AuditEntry) -> str:
        self.entries.append(entry)
        return "fake-hash"


def _record(
    tool: str = "db_query",
    outcome: str = "allow",
    principal: str = "alice",
    correlation_id: str = "c-1",
) -> ToolInvocationRecord:
    return ToolInvocationRecord(
        tool=tool,
        profile="main",
        op_class="READ",
        principal=principal,
        source_ip="127.0.0.1",
        correlation_id=correlation_id,
        outcome=outcome,
        latency_ms=1.2,
        row_count=5,
    )


def test_audit_integration_writes_one_entry_per_call() -> None:
    sink = CaptureSink()
    middleware = AuditMiddleware(sink=sink)

    middleware.record(_record())
    middleware.record(_record())

    assert len(sink.entries) == 2


def test_audit_integration_includes_correlation_id() -> None:
    sink = CaptureSink()
    middleware = AuditMiddleware(sink=sink)

    middleware.record(_record(correlation_id="corr-99"))

    assert sink.entries[0].request_id == "corr-99"


def test_audit_integration_maps_all_nist_au3_fields() -> None:
    """NIST AU-3: who, source, action, target, outcome must all be present."""
    sink = CaptureSink()
    middleware = AuditMiddleware(sink=sink)
    middleware.record(_record(principal="bob", outcome="deny"))

    entry = sink.entries[0]
    assert entry.who == "bob"
    assert entry.source == "127.0.0.1"
    assert entry.action == "db_query"
    assert entry.target == "main"
    assert entry.outcome == "deny"


def test_audit_integration_meta_fields() -> None:
    sink = CaptureSink()
    middleware = AuditMiddleware(sink=sink)
    middleware.record(
        ToolInvocationRecord(
            tool="db_introspect",
            profile="pg_prod",
            op_class="ADMIN",
            principal="svc",
            source_ip="10.0.0.1",
            correlation_id="cid-1",
            outcome="allow",
            latency_ms=42.5,
            row_count=0,
            error_code="",
        )
    )
    entry = sink.entries[0]
    assert entry.meta["op_class"] == "ADMIN"
    assert entry.meta["latency_ms"] == 42.5
    assert entry.meta["row_count"] == 0


def test_build_audit_middleware_with_path(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    middleware = build_audit_middleware(audit_path=log_path, key="secret-key")
    assert isinstance(middleware, AuditMiddleware)

    middleware.record(_record())
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["action"] == "db_query"


def test_build_audit_middleware_with_explicit_sink() -> None:
    sink = CaptureSink()
    middleware = build_audit_middleware(sink=sink)
    middleware.record(_record())
    assert len(sink.entries) == 1


def test_build_audit_middleware_null_sink_no_path() -> None:
    """Without path or sink, a NullSink is used — no file written."""
    middleware = build_audit_middleware()
    assert isinstance(middleware._sink, _NullSink)
    # Must not raise
    middleware.record(_record())


def test_null_sink_returns_empty_hash() -> None:
    sink = _NullSink()
    entry = AuditEntry(who="x", source="y", action="z", target="t", outcome="allow", request_id="r")
    result = sink.write(entry)
    assert result == ""


def test_audit_integration_hmac_chain_verifies(tmp_path: Path) -> None:
    log_path = tmp_path / "audit.jsonl"
    middleware = build_audit_middleware(audit_path=log_path, key="hmac-key")

    for i in range(3):
        middleware.record(_record(correlation_id=f"c-{i}"))

    assert HMACChainSink.verify(path=log_path, key="hmac-key") is True


def test_make_invocation_record_computes_latency() -> None:
    start = time.perf_counter()
    rec = make_invocation_record(
        tool="db_ping",
        profile="main",
        op_class="READ",
        principal="alice",
        source_ip="127.0.0.1",
        correlation_id="x",
        outcome="allow",
        start_time=start,
    )
    assert rec.latency_ms >= 0


def test_record_timed_helper() -> None:
    sink = CaptureSink()
    middleware = AuditMiddleware(sink=sink)
    start = time.perf_counter()
    middleware.record_timed(
        tool="db_query",
        profile="main",
        op_class="READ",
        principal="svc",
        source_ip="127.0.0.1",
        correlation_id="c-t",
        row_count=10,
        outcome="allow",
        start_time=start,
    )
    assert len(sink.entries) == 1
    assert sink.entries[0].meta["row_count"] == 10
