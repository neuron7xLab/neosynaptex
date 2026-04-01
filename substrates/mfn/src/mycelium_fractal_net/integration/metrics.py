"""
Prometheus metrics for MyceliumFractalNet API.

Provides HTTP request metrics, latency histograms, and a /metrics endpoint
for Prometheus scraping.

Metrics Exposed:
    mfn_http_requests_total: Counter of HTTP requests (labels: endpoint, method, status)
    mfn_http_request_duration_seconds: Histogram of request latency (labels: endpoint, method)
    mfn_http_requests_in_progress: Gauge of currently processing requests

Usage:
    from mycelium_fractal_net.integration.metrics import MetricsMiddleware, metrics_endpoint

    app.add_middleware(MetricsMiddleware)
    app.add_route("/metrics", metrics_endpoint)

Reference: docs/MFN_BACKLOG.md#MFN-OBS-001
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .api_config import MetricsConfig, get_api_config

if TYPE_CHECKING:
    from starlette.responses import Response as StarletteResponse

# Try to import prometheus_client, provide fallback if not available
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"
    Counter = None  # type: ignore[misc,assignment]
    Histogram = None  # type: ignore[misc,assignment]
    Gauge = None  # type: ignore[misc,assignment]

    def generate_latest() -> bytes:  # type: ignore[misc]
        return b"# prometheus_client not installed\n"


# Define metrics (singleton pattern to avoid duplicate registration)
# Using a module-level dict to store created metrics

_METRICS_CREATED = False
REQUEST_COUNTER: Any = None
REQUEST_LATENCY: Any = None
REQUESTS_IN_PROGRESS: Any = None


def _create_metrics() -> None:
    """Create metrics if not already created."""
    global _METRICS_CREATED, REQUEST_COUNTER, REQUEST_LATENCY, REQUESTS_IN_PROGRESS

    if _METRICS_CREATED:
        return

    if PROMETHEUS_AVAILABLE:
        from prometheus_client import REGISTRY

        # Check if metrics already exist in registry
        try:
            REQUEST_COUNTER = Counter(
                "mfn_http_requests_total",
                "Total number of HTTP requests",
                ["endpoint", "method", "status"],
            )
        except ValueError:
            # Already registered - get existing
            # Counter stores name without "_total" suffix internally
            metric_name = "mfn_http_requests"
            for collector in REGISTRY._names_to_collectors.values():
                if hasattr(collector, "_name") and collector._name == metric_name:
                    REQUEST_COUNTER = collector
                    break

        try:
            REQUEST_LATENCY = Histogram(
                "mfn_http_request_duration_seconds",
                "HTTP request latency in seconds",
                ["endpoint", "method"],
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            )
        except ValueError:
            # Already registered
            metric_name = "mfn_http_request_duration_seconds"
            for collector in REGISTRY._names_to_collectors.values():
                if hasattr(collector, "_name") and collector._name == metric_name:
                    REQUEST_LATENCY = collector
                    break

        try:
            REQUESTS_IN_PROGRESS = Gauge(
                "mfn_http_requests_in_progress",
                "Number of HTTP requests currently being processed",
                ["endpoint", "method"],
            )
        except ValueError:
            # Already registered
            metric_name = "mfn_http_requests_in_progress"
            for collector in REGISTRY._names_to_collectors.values():
                if hasattr(collector, "_name") and collector._name == metric_name:
                    REQUESTS_IN_PROGRESS = collector
                    break
    # When prometheus_client is not available, metrics stay as None
    # The middleware will handle None checks

    _METRICS_CREATED = True


# Initialize metrics on module load
_create_metrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting HTTP request metrics.

    Records:
        - Request count (by endpoint, method, status)
        - Request latency (by endpoint, method)
        - In-progress requests (by endpoint, method)

    Attributes:
        config: Metrics configuration.
    """

    def __init__(
        self,
        app: Any,
        config: MetricsConfig | None = None,
    ) -> None:
        """
        Initialize metrics middleware.

        Args:
            app: The ASGI application.
            config: Metrics configuration. If None, uses global config.
        """
        super().__init__(app)
        self.config = config or get_api_config().metrics

    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for metric labels.

        Removes path parameters to prevent label explosion.

        Args:
            path: Request path.

        Returns:
            str: Normalized endpoint path.
        """
        metrics_path = get_api_config().metrics.endpoint
        # Keep known endpoints as-is
        known_endpoints = [
            "/health",
            "/validate",
            "/simulate",
            "/nernst",
            "/federated/aggregate",
            metrics_path,
            "/metrics" if metrics_path != "/metrics" else None,
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        for endpoint in [path for path in known_endpoints if path]:
            if path == endpoint or path.startswith(endpoint + "/"):
                return endpoint

        # For unknown paths, use a generic label
        return "/other"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """
        Process request and collect metrics.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            Response: Route response.
        """
        if not self.config.enabled:
            return await call_next(request)

        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method

        # Track in-progress requests
        if REQUESTS_IN_PROGRESS is not None:
            REQUESTS_IN_PROGRESS.labels(endpoint=endpoint, method=method).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        finally:
            # Record duration
            duration = time.perf_counter() - start_time
            if REQUEST_LATENCY is not None:
                REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

            # Decrement in-progress
            if REQUESTS_IN_PROGRESS is not None:
                REQUESTS_IN_PROGRESS.labels(endpoint=endpoint, method=method).dec()

            # Increment request counter
            if REQUEST_COUNTER is not None:
                REQUEST_COUNTER.labels(endpoint=endpoint, method=method, status=status_code).inc()

        return response


async def metrics_endpoint(request: Request) -> Response:
    """
    Endpoint handler for /metrics.

    Returns Prometheus-formatted metrics.

    Args:
        request: Incoming request.

    Returns:
        Response: Prometheus metrics in text format.
    """
    config = get_api_config().metrics
    if not config.enabled:
        # Return 404 to avoid leaking information when metrics are disabled
        return Response(status_code=404)

    metrics_output = generate_latest()

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )


def is_prometheus_available() -> bool:
    """
    Check if prometheus_client is available.

    Returns:
        bool: True if prometheus_client is installed.
    """
    return PROMETHEUS_AVAILABLE


__all__ = [
    "REQUESTS_IN_PROGRESS",
    "REQUEST_COUNTER",
    "REQUEST_LATENCY",
    "MetricsMiddleware",
    "is_prometheus_available",
    "metrics_endpoint",
]
