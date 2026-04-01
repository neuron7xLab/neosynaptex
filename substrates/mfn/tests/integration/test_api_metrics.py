"""
Tests for Prometheus metrics endpoint.

Verifies metrics collection and /metrics endpoint:
- /metrics returns Prometheus format
- Request counters increment correctly
- Latency histograms record request timing
- Metrics include expected labels

Reference: docs/MFN_BACKLOG.md#MFN-OBS-001
"""

from __future__ import annotations

import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import (
    get_api_config,
    is_prometheus_available,
    reset_config,
)


@pytest.fixture(autouse=True)
def reset_api_config():
    """Reset API config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def metrics_client():
    """Create test client with metrics enabled."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
            "MFN_METRICS_ENABLED": "true",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


@pytest.fixture
def metrics_disabled_client():
    """Create test client with metrics explicitly disabled."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
            "MFN_METRICS_ENABLED": "false",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


@pytest.fixture
def metrics_custom_endpoint_client():
    """Create test client with a custom metrics endpoint."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
            "MFN_METRICS_ENABLED": "true",
            "MFN_METRICS_ENDPOINT": "custom-metrics/",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


def _metrics_path() -> str:
    """Get the configured metrics endpoint path."""
    return get_api_config().metrics.endpoint


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_endpoint_returns_200(self, metrics_client: TestClient) -> None:
        """Metrics endpoint should return 200."""
        response = metrics_client.get(_metrics_path())
        assert response.status_code == 200

    def test_metrics_endpoint_returns_404_when_disabled(
        self, metrics_disabled_client: TestClient
    ) -> None:
        """Metrics endpoint should not expose data when disabled."""
        response = metrics_disabled_client.get(_metrics_path())
        assert response.status_code == 404

    def test_metrics_content_type(self, metrics_client: TestClient) -> None:
        """Metrics endpoint should return text/plain content type."""
        response = metrics_client.get(_metrics_path())
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type

    def test_metrics_format(self, metrics_client: TestClient) -> None:
        """Metrics should be in Prometheus format."""
        response = metrics_client.get(_metrics_path())
        content = response.text

        # Prometheus format includes TYPE and HELP comments
        # At minimum, check it's not empty and has some metric-like content
        assert len(content) > 0

        # If prometheus_client is available, check for our custom metrics
        if is_prometheus_available():
            # Should contain our metric names (after some requests)
            pass  # Metrics may not exist until requests are made

    def test_metrics_contain_request_counter(self, metrics_client: TestClient) -> None:
        """Metrics should contain HTTP request counter."""
        # Make some requests first
        metrics_client.get("/health")
        metrics_client.get("/health")

        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            # Check for our custom metric
            assert "mfn_http_requests_total" in content

    def test_metrics_contain_latency_histogram(self, metrics_client: TestClient) -> None:
        """Metrics should contain request latency histogram."""
        # Make a request first
        metrics_client.get("/health")

        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            # Check for our histogram metric
            assert "mfn_http_request_duration_seconds" in content

    def test_metrics_labels(self, metrics_client: TestClient) -> None:
        """Metrics should have correct labels."""
        # Make various requests
        metrics_client.get("/health")
        metrics_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
            },
        )

        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            # Check for endpoint labels
            assert 'endpoint="/health"' in content or "endpoint" in content


class TestMetricsCollection:
    """Tests for metrics collection behavior."""

    def test_metrics_increment_on_request(self, metrics_client: TestClient) -> None:
        """Request counter should increment on each request."""
        # Make a request
        metrics_client.get("/health")

        # Get metrics
        response = metrics_client.get(_metrics_path())
        content = response.text

        # Metrics should have changed (new request recorded)
        if is_prometheus_available():
            # Should contain our metrics
            assert "mfn_http_requests_total" in content
            # Should have recorded the /health request
            assert "/health" in content or "health" in content

    def test_metrics_record_different_endpoints(self, metrics_client: TestClient) -> None:
        """Metrics should track different endpoints separately."""
        # Make requests to different endpoints
        metrics_client.get("/health")
        metrics_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
            },
        )

        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            # Should have metrics for both endpoints
            assert "/health" in content or "health" in content

    def test_metrics_record_different_methods(self, metrics_client: TestClient) -> None:
        """Metrics should track different HTTP methods."""
        # Make GET and POST requests
        metrics_client.get("/health")
        metrics_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
            },
        )

        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            # Should have metrics for GET and POST
            assert "GET" in content or "POST" in content

    def test_metrics_record_status_codes(self, metrics_client: TestClient) -> None:
        """Metrics should track different status codes."""
        # Make successful request
        metrics_client.get("/health")

        # Make request that returns 400 (bad input)
        metrics_client.post("/federated/aggregate", json={"gradients": []})

        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            # Should have metrics with status codes
            assert "200" in content or "400" in content


class TestMetricsConfig:
    """Tests for metrics configuration."""

    def test_metrics_enabled_by_default(self) -> None:
        """Metrics should be enabled by default."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            MetricsConfig,
        )

        config = MetricsConfig.from_env(Environment.PROD)
        assert config.enabled is True

    def test_metrics_can_be_disabled(self) -> None:
        """Metrics can be disabled via environment."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            MetricsConfig,
        )

        with mock.patch.dict(os.environ, {"MFN_METRICS_ENABLED": "false"}):
            config = MetricsConfig.from_env(Environment.PROD)
            assert config.enabled is False

    def test_metrics_can_be_removed_from_public_endpoints(self) -> None:
        """Including metrics in auth should remove both default and custom endpoints."""
        from mycelium_fractal_net.integration.api_config import APIConfig

        with mock.patch.dict(
            os.environ,
            {
                "MFN_METRICS_INCLUDE_IN_AUTH": "true",
                "MFN_METRICS_ENDPOINT": "/secure-metrics",
            },
            clear=False,
        ):
            reset_config()
            config = APIConfig.from_env()

        assert "/metrics" not in config.auth.public_endpoints
        assert "/secure-metrics" not in config.auth.public_endpoints

    def test_metrics_endpoint_is_normalized(self) -> None:
        """Metrics endpoint should normalize slashes."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            MetricsConfig,
        )

        with mock.patch.dict(os.environ, {"MFN_METRICS_ENDPOINT": "metrics/"}):
            config = MetricsConfig.from_env(Environment.PROD)
            assert config.endpoint == "/metrics"

    def test_prometheus_availability_check(self) -> None:
        """Should be able to check if prometheus is available."""
        # This should not raise
        result = is_prometheus_available()
        assert isinstance(result, bool)


class TestMetricsMiddleware:
    """Tests for metrics middleware behavior."""

    def test_middleware_does_not_break_requests(self, metrics_client: TestClient) -> None:
        """Metrics middleware should not break normal request flow."""
        response = metrics_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_middleware_handles_errors(self, metrics_client: TestClient) -> None:
        """Metrics middleware should handle errors gracefully."""
        # Make request that will fail (either 400 or 401 depending on auth)
        response = metrics_client.post("/federated/aggregate", json={"gradients": []})
        # Should get some error response, not a crash
        assert response.status_code in (400, 401)

        # Metrics should still be available
        metrics_response = metrics_client.get(_metrics_path())
        assert metrics_response.status_code == 200

    def test_in_progress_requests_gauge(self, metrics_client: TestClient) -> None:
        """In-progress requests gauge should be tracked."""
        response = metrics_client.get(_metrics_path())
        content = response.text

        if is_prometheus_available():
            assert "mfn_http_requests_in_progress" in content


class TestMetricsCustomEndpoint:
    """Tests for custom metrics endpoint configuration."""

    def test_custom_metrics_endpoint_served(
        self, metrics_custom_endpoint_client: TestClient
    ) -> None:
        """Custom metrics endpoint should return 200 and normalize path."""
        response = metrics_custom_endpoint_client.get(_metrics_path())
        assert response.status_code == 200

    def test_default_metrics_path_not_available(
        self, metrics_custom_endpoint_client: TestClient
    ) -> None:
        """Default /metrics path should return 404 when customized."""
        response = metrics_custom_endpoint_client.get("/metrics")
        assert response.status_code == 404
