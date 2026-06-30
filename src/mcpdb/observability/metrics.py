from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import prometheus_client as prom
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send


class Metrics:
    """Named Prometheus counters and histograms for mcpdb tool invocations.

    All metrics are registered on an isolated ``CollectorRegistry`` so tests
    can instantiate independent ``Metrics`` objects without ``ValueError:
    Duplicated timeseries`` errors from the default global registry.
    """

    def __init__(self, registry: prom.CollectorRegistry | None = None) -> None:
        self._registry = registry or prom.CollectorRegistry()

        # mcpdb_requests_total{tool,op_class,outcome}
        self.requests_total = prom.Counter(
            "mcpdb_requests_total",
            "Total tool invocations labelled by tool name, operation class, and outcome",
            labelnames=["tool", "op_class", "outcome"],
            registry=self._registry,
        )

        # mcpdb_request_duration_seconds{tool} — histogram
        self.request_duration_seconds = prom.Histogram(
            "mcpdb_request_duration_seconds",
            "Tool invocation latency in seconds",
            labelnames=["tool"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, float("inf")),
            registry=self._registry,
        )

        # mcpdb_rows_returned_total{tool}
        self.rows_returned_total = prom.Counter(
            "mcpdb_rows_returned_total",
            "Total rows returned across tool invocations",
            labelnames=["tool"],
            registry=self._registry,
        )

        # mcpdb_query_timeouts_total{tool}
        self.query_timeouts_total = prom.Counter(
            "mcpdb_query_timeouts_total",
            "Total query timeouts by tool",
            labelnames=["tool"],
            registry=self._registry,
        )

        # mcpdb_policy_denials_total{tool,op_class}
        self.policy_denials_total = prom.Counter(
            "mcpdb_policy_denials_total",
            "Total policy-denied requests by tool and operation class",
            labelnames=["tool", "op_class"],
            registry=self._registry,
        )

    def record_request(
        self, tool: str, op_class: str, outcome: str, duration_s: float, rows: int = 0
    ) -> None:
        """Convenience method to record a single completed tool invocation."""
        self.requests_total.labels(tool=tool, op_class=op_class, outcome=outcome).inc()
        self.request_duration_seconds.labels(tool=tool).observe(duration_s)
        if rows:
            self.rows_returned_total.labels(tool=tool).inc(rows)

    def record_timeout(self, tool: str) -> None:
        self.query_timeouts_total.labels(tool=tool).inc()

    def record_denial(self, tool: str, op_class: str) -> None:
        self.policy_denials_total.labels(tool=tool, op_class=op_class).inc()

    @contextmanager
    def measure(self, tool: str) -> Iterator[None]:
        """Context manager that records duration and yields.  Caller owns outcome."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.request_duration_seconds.labels(tool=tool).observe(elapsed)

    def text_output(self) -> str:
        """Return Prometheus text-format exposition string."""
        return prom.generate_latest(self._registry).decode("utf-8")


def build_metrics(registry: prom.CollectorRegistry | None = None) -> Metrics:
    """Factory — returns a fresh Metrics instance."""
    return Metrics(registry=registry)


# ──────────────────────────────────────────────────────────────────────────────
# /metrics ASGI middleware for HTTP transport
# ──────────────────────────────────────────────────────────────────────────────


class MetricsMiddleware:
    """ASGI middleware that instruments every request through the HTTP transport.

    Wraps the main ASGI app and exposes ``/metrics`` on a side-channel path that
    Prometheus can scrape.
    """

    def __init__(self, app: ASGIApp, metrics: Metrics) -> None:
        self._app = app
        self._metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope)
            if request.url.path == "/metrics":
                body = self._metrics.text_output().encode("utf-8")
                response = PlainTextResponse(
                    content=body.decode("utf-8"),
                    media_type=prom.CONTENT_TYPE_LATEST,
                )
                await response(scope, receive, send)
                return
        await self._app(scope, receive, send)


def metrics_route(metrics: Metrics) -> Callable[..., Any]:
    """Return a Starlette-compatible route handler for ``/metrics``."""

    async def handler(_: Request) -> Response:
        return PlainTextResponse(
            content=metrics.text_output(),
            media_type=prom.CONTENT_TYPE_LATEST,
        )

    return handler


def add_metrics_route(app: Starlette, metrics: Metrics) -> None:
    """Append a ``/metrics`` route to an existing Starlette app in-place."""
    app.routes.append(Route("/metrics", endpoint=metrics_route(metrics), methods=["GET"]))
