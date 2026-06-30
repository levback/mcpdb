from __future__ import annotations

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mcpdb.observability.tracing import (
    build_in_memory_exporter,
    configure_tracing,
    get_tracer,
    span_context_from_baggage,
)


def test_tracing_span_starts_and_ends() -> None:
    """configure_tracing with an in-memory exporter must capture completed spans."""
    exporter = build_in_memory_exporter()
    provider = configure_tracing(service_name="test-mcpdb", exporter=exporter)

    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("test.op") as span:
        span.set_attribute("tool", "db_ping")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test.op"
    assert spans[0].attributes is not None
    assert spans[0].attributes.get("tool") == "db_ping"


def test_tracing_context_propagates_to_db() -> None:
    """Nested spans must form a parent-child relationship."""
    exporter = build_in_memory_exporter()
    provider = configure_tracing(service_name="test-mcpdb-ctx", exporter=exporter)

    tracer = provider.get_tracer("test")
    with (
        tracer.start_as_current_span("server.request"),
        tracer.start_as_current_span("db.execute") as child,
    ):
        child.set_attribute("db.system", "sqlite")

    spans = exporter.get_finished_spans()
    assert len(spans) == 2

    names = {s.name for s in spans}
    assert "server.request" in names
    assert "db.execute" in names

    # child span's parent must be the server.request span
    parent_span = next(s for s in spans if s.name == "server.request")
    child_span = next(s for s in spans if s.name == "db.execute")
    assert child_span.parent is not None
    assert child_span.parent.span_id == parent_span.context.span_id


def test_get_tracer_returns_tracer() -> None:
    configure_tracing(service_name="tracer-test", exporter=build_in_memory_exporter())
    tracer = get_tracer("mcpdb.test")
    assert tracer is not None


def test_build_in_memory_exporter_is_fresh() -> None:
    e = build_in_memory_exporter()
    assert isinstance(e, InMemorySpanExporter)
    assert e.get_finished_spans() == ()


def test_span_context_from_baggage_with_data() -> None:
    headers = span_context_from_baggage({"correlation_id": "abc-123", "principal": "alice"})
    assert headers["x-correlation-id"] == "abc-123"
    assert headers["x-principal"] == "alice"


def test_span_context_from_baggage_empty() -> None:
    headers = span_context_from_baggage({})
    assert headers == {}


def test_configure_tracing_no_exporter_does_not_raise() -> None:
    """Without OTEL_EXPORTER_OTLP_ENDPOINT, no exporter is created and no error is raised."""
    import os

    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    provider = configure_tracing(service_name="no-export")
    # Should still return a provider
    assert provider is not None
