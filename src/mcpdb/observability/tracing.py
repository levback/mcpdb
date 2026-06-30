from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

_PROVIDER: TracerProvider | None = None
_NOOP_TRACER = trace.get_tracer(__name__)


def configure_tracing(
    service_name: str = "mcpdb",
    exporter: SpanExporter | None = None,
) -> TracerProvider:
    """Configure the global OTel tracer provider.

    When ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set and no custom exporter is
    provided, an OTLP gRPC exporter is created automatically.  If neither is
    configured, traces are silently discarded (no-op).

    Returns the configured ``TracerProvider`` for inspection in tests.
    """
    global _PROVIDER  # noqa: PLW0603  — intentional global singleton for OTel

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": _mcpdb_version(),
        }
    )

    provider = TracerProvider(resource=resource)

    resolved_exporter = exporter or _build_default_exporter()
    if resolved_exporter is not None:
        if isinstance(resolved_exporter, InMemorySpanExporter):
            # Test determinism: export on span end so assertions can read spans immediately.
            provider.add_span_processor(SimpleSpanProcessor(resolved_exporter))
        else:
            provider.add_span_processor(BatchSpanProcessor(resolved_exporter))

    # OTel allows setting the process-global provider only once.
    # Keep an internal provider reference for deterministic tests and local usage.
    if _PROVIDER is None:
        trace.set_tracer_provider(provider)
    _PROVIDER = provider
    return provider


def get_tracer(name: str = "mcpdb") -> trace.Tracer:
    """Return a module-scoped tracer from the currently active provider."""
    if _PROVIDER is not None:
        return _PROVIDER.get_tracer(name)
    return trace.get_tracer(name)


def build_in_memory_exporter() -> InMemorySpanExporter:
    """Factory for test-only in-memory span capture."""
    return InMemorySpanExporter()


def _build_default_exporter() -> SpanExporter | None:
    """Build an OTLP exporter if ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return None

    insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true"

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
    except ImportError:  # pragma: no cover
        return None


def _mcpdb_version() -> str:
    try:
        from mcpdb import __version__

        return str(__version__)
    except ImportError:  # pragma: no cover
        return "unknown"


def span_context_from_baggage(
    baggage: dict[str, Any],
) -> dict[str, str]:
    """Extract correlation headers for propagation into downstream calls."""
    headers: dict[str, str] = {}
    if correlation_id := baggage.get("correlation_id"):
        headers["x-correlation-id"] = str(correlation_id)
    if principal := baggage.get("principal"):
        headers["x-principal"] = str(principal)
    return headers
