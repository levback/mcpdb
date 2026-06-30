from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcpdb.observability.logging import get_logger
from mcpdb.security.audit import AuditEntry, AuditSink, HMACChainSink

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class ToolInvocationRecord:
    """Immutable record of a single tool call for audit emission.

    Maps to the Audit Entry fields mandated by NIST AU-2/AU-3.
    """

    tool: str
    profile: str
    op_class: str
    principal: str
    source_ip: str
    correlation_id: str
    outcome: str  # "allow" | "deny" | "error"
    latency_ms: float
    row_count: int = 0
    error_code: str = ""
    ts: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


class AuditMiddleware:
    """Writes one :class:`AuditEntry` per tool invocation via the given sink.

    Usage::

        middleware = AuditMiddleware(sink=HMACChainSink(path, key="secret"))
        record = ToolInvocationRecord(...)
        middleware.record(record)
    """

    def __init__(self, sink: AuditSink) -> None:
        self._sink = sink

    def record(self, invocation: ToolInvocationRecord) -> None:
        """Write one audit entry and emit a structured log line.

        NIST AU-9: the HMAC-chained sink ensures tamper-evidence.
        NIST AU-3: includes who, when, source, action, target, outcome.
        """
        entry = AuditEntry(
            who=invocation.principal,
            source=invocation.source_ip,
            action=invocation.tool,
            target=invocation.profile,
            outcome=invocation.outcome,
            request_id=invocation.correlation_id,
            meta={
                "op_class": invocation.op_class,
                "latency_ms": round(invocation.latency_ms, 3),
                "row_count": invocation.row_count,
                "error_code": invocation.error_code,
            },
        )
        self._sink.write(entry)
        LOGGER.info(
            "tool_invocation",
            tool=invocation.tool,
            profile=invocation.profile,
            op_class=invocation.op_class,
            outcome=invocation.outcome,
            latency_ms=round(invocation.latency_ms, 3),
            row_count=invocation.row_count,
            correlation_id=invocation.correlation_id,
        )  # NIST AU-3: structured event per invocation

    def record_timed(
        self,
        *,
        tool: str,
        profile: str,
        op_class: str,
        principal: str,
        source_ip: str,
        correlation_id: str,
        row_count: int = 0,
        error_code: str = "",
        outcome: str = "allow",
        start_time: float | None = None,
    ) -> None:
        """Convenience wrapper: compute latency from ``start_time`` and record."""
        latency_ms = (time.perf_counter() - (start_time or time.perf_counter())) * 1000
        self.record(
            ToolInvocationRecord(
                tool=tool,
                profile=profile,
                op_class=op_class,
                principal=principal,
                source_ip=source_ip,
                correlation_id=correlation_id,
                outcome=outcome,
                latency_ms=latency_ms,
                row_count=row_count,
                error_code=error_code,
            )
        )


def build_audit_middleware(
    audit_path: Path | None = None,
    *,
    key: str | None = None,
    sink: AuditSink | None = None,
) -> AuditMiddleware:
    """Factory that builds :class:`AuditMiddleware` from either a file path or
    an explicit sink.

    If neither ``audit_path`` nor ``sink`` is provided, a no-op in-memory sink
    is created for testing purposes.
    """
    if sink is not None:
        return AuditMiddleware(sink=sink)

    if audit_path is not None and key:
        return AuditMiddleware(sink=HMACChainSink(path=audit_path, key=key))

    # Fallback: in-memory NullSink — writes are structlog-visible only
    return AuditMiddleware(sink=_NullSink())


class _NullSink(AuditSink):
    """A no-op sink that discards audit entries — for dev/test only."""

    def write(self, entry: AuditEntry) -> str:  # noqa: ARG002
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# Typed helpers for integration with ToolService
# ──────────────────────────────────────────────────────────────────────────────


def make_invocation_record(
    *,
    tool: str,
    profile: str,
    op_class: str,
    principal: str,
    source_ip: str,
    correlation_id: str,
    outcome: str,
    start_time: float,
    row_count: int = 0,
    error_code: str = "",
    extra_meta: dict[str, Any] | None = None,
) -> ToolInvocationRecord:
    """Convenience constructor for ToolInvocationRecord."""
    latency_ms = (time.perf_counter() - start_time) * 1000
    return ToolInvocationRecord(
        tool=tool,
        profile=profile,
        op_class=op_class,
        principal=principal,
        source_ip=source_ip,
        correlation_id=correlation_id,
        outcome=outcome,
        latency_ms=latency_ms,
        row_count=row_count,
        error_code=error_code,
    )
