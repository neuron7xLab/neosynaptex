"""SLO validation tests for API endpoints.

Tests that key API endpoints meet their Service Level Objectives under
controlled load conditions. Uses stub backends for deterministic results.
"""

from __future__ import annotations

import os
import threading

import pytest
from fastapi.testclient import TestClient

from mlsdm.api.app import app
from mlsdm.config.perf_slo import (
    DEFAULT_ERROR_RATE_SLO,
    DEFAULT_LATENCY_SLO,
    LIVENESS_CHECK_SLO_MULTIPLIER,
    MODERATE_LOAD_ERROR_MULTIPLIER,
    MODERATE_LOAD_SLO_MULTIPLIER,
    READINESS_CHECK_SLO_MULTIPLIER,
    get_load_profile,
)
from tests.perf.utils import run_load_test

# Disable rate limiting for performance tests to avoid 429 errors
# This allows us to test actual endpoint performance, not rate limiter behavior
os.environ["DISABLE_RATE_LIMIT"] = "1"
WARMUP_REQUESTS = int(os.getenv("PERF_WARMUP_REQUESTS", "10"))
WARMUP_ENABLED = os.getenv("PERF_WARMUP_ENABLED", "1") != "0"

_client_local = threading.local()


def _get_client() -> TestClient:
    """Return a thread-local TestClient to avoid cross-thread event loop issues."""
    client = getattr(_client_local, "client", None)
    if client is None:
        client = TestClient(app)
        _client_local.client = client
    return client


@pytest.mark.benchmark
class TestGenerateEndpointSLO:
    """SLO tests for POST /generate endpoint."""

    def test_generate_latency_light_load(self, deterministic_seed: int) -> None:
        """Validate /generate latency under light load meets SLO.

        SLO: P95 latency < 150ms under light load (50 requests, 5 concurrent).
        Note: Warmup requests are excluded to avoid cold-start bias.
        """
        profile = get_load_profile("light")

        if WARMUP_ENABLED:
            for _ in range(WARMUP_REQUESTS):
                response = _get_client().post(
                    "/generate",
                    json={
                        "prompt": "Warmup request",
                        "max_tokens": 10,
                        "moral_value": 0.5,
                    },
                )
                assert response.status_code in (200, 201), (
                    f"Unexpected status during warmup: {response.status_code}"
                )

        def make_request() -> None:
            response = _get_client().post(
                "/generate",
                json={
                    "prompt": "Test prompt for SLO validation",
                    "max_tokens": 50,
                    "moral_value": 0.8,
                },
            )
            assert response.status_code in (200, 201), f"Unexpected status: {response.status_code}"

        results = run_load_test(
            operation=make_request,
            n_requests=profile.total_requests,
            concurrency=profile.concurrency,
        )

        # Verify SLO compliance
        is_compliant, message = DEFAULT_LATENCY_SLO.check_p95_compliance(
            results.p95_latency_ms,
            strict=False,
        )
        assert is_compliant, (
            f"P95 latency {results.p95_latency_ms:.2f}ms exceeds SLO. {message}"
        )
        assert results.error_rate_percent <= DEFAULT_ERROR_RATE_SLO.max_error_rate_percent, (
            f"Error rate {results.error_rate_percent:.2f}% exceeds SLO "
            f"({DEFAULT_ERROR_RATE_SLO.max_error_rate_percent}%)"
        )

    def test_generate_error_rate_light_load(self, deterministic_seed: int) -> None:
        """Validate /generate error rate under light load meets SLO.

        SLO: Error rate < 1% under stable conditions.
        """
        profile = get_load_profile("light")

        def make_request() -> None:
            response = _get_client().post(
                "/generate",
                json={
                    "prompt": "Another test prompt",
                    "max_tokens": 50,
                    "moral_value": 0.7,
                },
            )
            # Accept 2xx and 429 (rate limiting is expected behavior)
            assert response.status_code in (
                200,
                201,
                429,
            ), f"Unexpected status: {response.status_code}"

        results = run_load_test(
            operation=make_request,
            n_requests=profile.total_requests,
            concurrency=profile.concurrency,
        )

        # Error rate should be very low
        assert (
            results.error_rate_percent <= DEFAULT_ERROR_RATE_SLO.max_error_rate_percent
        ), f"Error rate {results.error_rate_percent:.2f}% exceeds SLO"

        # Availability should be high
        availability = 100.0 - results.error_rate_percent
        assert availability >= DEFAULT_ERROR_RATE_SLO.min_availability_percent, (
            f"Availability {availability:.2f}% below SLO "
            f"({DEFAULT_ERROR_RATE_SLO.min_availability_percent}%)"
        )


@pytest.mark.benchmark
class TestInferEndpointSLO:
    """SLO tests for POST /infer endpoint."""

    def test_infer_latency_light_load(self, deterministic_seed: int) -> None:
        """Validate /infer latency under light load meets SLO.

        SLO: P95 latency < 150ms under light load.
        """
        profile = get_load_profile("light")

        def make_request() -> None:
            response = _get_client().post(
                "/infer",
                json={
                    "prompt": "Test inference prompt",
                    "max_tokens": 50,
                    "secure_mode": False,
                    "aphasia_mode": "off",
                    "rag_enabled": False,
                },
            )
            assert response.status_code in (200, 201), f"Unexpected status: {response.status_code}"

        results = run_load_test(
            operation=make_request,
            n_requests=profile.total_requests,
            concurrency=profile.concurrency,
        )

        # Verify SLO compliance
        assert results.p95_latency_ms < DEFAULT_LATENCY_SLO.api_p95_ms, (
            f"P95 latency {results.p95_latency_ms:.2f}ms exceeds SLO "
            f"({DEFAULT_LATENCY_SLO.api_p95_ms}ms)"
        )


@pytest.mark.benchmark
class TestHealthEndpointSLO:
    """SLO tests for health check endpoints."""

    def test_liveness_latency(self, deterministic_seed: int) -> None:
        """Validate /health/liveness latency is very low.

        Liveness checks should be very fast but may be slower in CI
        due to virtualization overhead and concurrent testing.
        """
        profile = get_load_profile("light")

        def make_request() -> None:
            response = _get_client().get("/health/liveness")
            assert response.status_code == 200

        results = run_load_test(
            operation=make_request,
            n_requests=profile.total_requests,
            concurrency=profile.concurrency,
        )

        # Liveness checks have higher latency tolerance in CI
        # Due to virtualization overhead and concurrent testing
        # Use centralized multiplier for liveness endpoints
        liveness_latency_slo = DEFAULT_LATENCY_SLO.api_p50_ms * LIVENESS_CHECK_SLO_MULTIPLIER
        assert results.p95_latency_ms < liveness_latency_slo, (
            f"Health check P95 latency {results.p95_latency_ms:.2f}ms too high "
            f"(should be < {liveness_latency_slo}ms)"
        )

        # Health checks should never fail
        assert (
            results.error_rate_percent == 0.0
        ), f"Health checks failed {results.error_rate_percent:.2f}% of time"

    def test_readiness_latency(self, deterministic_seed: int) -> None:
        """Validate /health/readiness latency is low.

        Readiness checks may be slightly slower than liveness due to:
        - CPU usage sampling via psutil
        - System resource checks
        - CI environment virtualization overhead
        """
        profile = get_load_profile("light")

        def make_request() -> None:
            response = _get_client().get("/health/readiness")
            assert response.status_code == 200

        results = run_load_test(
            operation=make_request,
            n_requests=profile.total_requests,
            concurrency=profile.concurrency,
        )

        # Readiness checks have higher latency tolerance than liveness
        # Due to system resource checks (CPU, memory) that may be slow in CI
        # Use centralized multiplier for readiness endpoints
        readiness_latency_slo = DEFAULT_LATENCY_SLO.api_p95_ms * READINESS_CHECK_SLO_MULTIPLIER
        assert results.p95_latency_ms < readiness_latency_slo, (
            f"Readiness check P95 latency {results.p95_latency_ms:.2f}ms too high "
            f"(should be < {readiness_latency_slo}ms)"
        )


@pytest.mark.benchmark
@pytest.mark.slow
class TestModerateLoadSLO:
    """SLO tests under moderate load (200 requests, 10 concurrent)."""

    def test_generate_moderate_load(self, deterministic_seed: int) -> None:
        """Validate /generate maintains SLO under moderate load.

        SLO: P95 latency < 150ms, error rate < 1% with 200 requests.
        """
        profile = get_load_profile("moderate")

        def make_request() -> None:
            response = _get_client().post(
                "/generate",
                json={
                    "prompt": "Moderate load test prompt",
                    "max_tokens": 50,
                    "moral_value": 0.75,
                },
            )
            # Accept successful responses and rate limiting
            assert response.status_code in (200, 201, 429)

        results = run_load_test(
            operation=make_request,
            n_requests=profile.total_requests,
            concurrency=profile.concurrency,
        )

        # SLO should still be met under moderate load
        relaxed_latency_slo = DEFAULT_LATENCY_SLO.api_p95_ms * MODERATE_LOAD_SLO_MULTIPLIER
        assert results.p95_latency_ms < relaxed_latency_slo, (
            f"P95 latency {results.p95_latency_ms:.2f}ms exceeds relaxed SLO "
            f"under moderate load ({relaxed_latency_slo}ms)"
        )

        # Allow slightly higher error rate under load
        relaxed_error_slo = (
            DEFAULT_ERROR_RATE_SLO.max_error_rate_percent * MODERATE_LOAD_ERROR_MULTIPLIER
        )
        assert results.error_rate_percent <= relaxed_error_slo, (
            f"Error rate {results.error_rate_percent:.2f}% exceeds relaxed SLO "
            f"under moderate load ({relaxed_error_slo}%)"
        )
