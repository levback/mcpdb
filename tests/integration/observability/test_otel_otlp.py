from __future__ import annotations

import os

import pytest

from mcpdb.observability.tracing import configure_tracing


@pytest.mark.asyncio
async def test_integration_otel_export_to_collector() -> None:
    """Attempt OTLP export to a real collector; skip if none is configured."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        pytest.skip("OTEL_EXPORTER_OTLP_ENDPOINT is not set; skipping integration test")

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider = configure_tracing(service_name="mcpdb-integration", exporter=exporter)
    tracer = provider.get_tracer("integration")

    with tracer.start_as_current_span("integration.test") as span:
        span.set_attribute("test.run", True)

    provider.force_flush(timeout_millis=5000)
    # If no exception was raised, export was successful
