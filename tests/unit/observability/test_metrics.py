from __future__ import annotations

import prometheus_client as prom

from mcpdb.observability.metrics import Metrics, MetricsMiddleware, build_metrics


def _fresh() -> Metrics:
    return Metrics(registry=prom.CollectorRegistry())


def test_metrics_request_counter_increments() -> None:
    m = _fresh()
    m.requests_total.labels(tool="db_query", op_class="READ", outcome="allow").inc()
    text = m.text_output()
    assert "mcpdb_requests_total" in text
    assert 'tool="db_query"' in text


def test_metrics_histogram_records_latency() -> None:
    m = _fresh()
    m.request_duration_seconds.labels(tool="db_ping").observe(0.123)
    text = m.text_output()
    assert "mcpdb_request_duration_seconds" in text
    assert 'tool="db_ping"' in text


def test_metrics_endpoint_serves_text_format() -> None:
    m = _fresh()
    m.requests_total.labels(tool="db_introspect", op_class="READ", outcome="allow").inc(3)
    text = m.text_output()
    # Prometheus text format must start with "# HELP" or include metric names
    assert "mcpdb_requests_total" in text
    assert "3.0" in text or "3" in text  # counter value


def test_metrics_record_request_helper() -> None:
    m = _fresh()
    m.record_request(tool="db_query", op_class="WRITE", outcome="deny", duration_s=0.05, rows=0)
    text = m.text_output()
    assert 'outcome="deny"' in text


def test_metrics_record_timeout() -> None:
    m = _fresh()
    m.record_timeout("db_query")
    text = m.text_output()
    assert "mcpdb_query_timeouts_total" in text


def test_metrics_record_denial() -> None:
    m = _fresh()
    m.record_denial("db_query", "WRITE")
    text = m.text_output()
    assert "mcpdb_policy_denials_total" in text


def test_metrics_rows_returned_counter() -> None:
    m = _fresh()
    m.record_request(tool="db_query", op_class="READ", outcome="allow", duration_s=0.01, rows=100)
    text = m.text_output()
    assert "mcpdb_rows_returned_total" in text


def test_metrics_measure_context_manager() -> None:
    m = _fresh()
    with m.measure("db_ping"):
        pass  # just ensure it doesn't raise and records something
    text = m.text_output()
    assert "mcpdb_request_duration_seconds" in text


def test_build_metrics_factory() -> None:
    m = build_metrics(registry=prom.CollectorRegistry())
    assert isinstance(m, Metrics)
    assert m.text_output() != ""


def test_metrics_middleware_serves_metrics_path() -> None:
    """MetricsMiddleware must intercept /metrics and return Prometheus text."""

    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    m = _fresh()
    m.requests_total.labels(tool="db_ping", op_class="READ", outcome="allow").inc()

    async def index(request):
        return PlainTextResponse("ok")

    base_app = Starlette(routes=[Route("/", endpoint=index)])
    wrapped = MetricsMiddleware(base_app, m)

    client = TestClient(wrapped)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "mcpdb_requests_total" in resp.text
