"""
Small-scale API performance tests.

Quick performance sanity checks that can run in CI.
Uses synchronous requests with basic latency assertions.

For full load testing, use load_tests/locustfile.py

Reference: docs/MFN_BACKLOG.md#MFN-TEST-001
"""

from __future__ import annotations

import os
import statistics
import time
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import get_api_config, reset_config


@pytest.fixture(autouse=True)
def reset_api_config():
    """Reset API config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def perf_client():
    """Create test client for performance testing."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


class TestAPIPerformanceBasics:
    """Basic performance tests for API endpoints."""

    def test_health_endpoint_latency(self, perf_client: TestClient) -> None:
        """Health endpoint should respond quickly (< 100ms)."""
        latencies = []

        for _ in range(10):
            start = time.perf_counter()
            response = perf_client.get("/health")
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            assert response.status_code == 200

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # Health check should be very fast
        assert avg_latency < 100, f"Avg latency {avg_latency:.2f}ms exceeds 100ms"
        assert p95_latency < 200, f"P95 latency {p95_latency:.2f}ms exceeds 200ms"

    def test_nernst_endpoint_latency(self, perf_client: TestClient) -> None:
        """Nernst endpoint should respond within acceptable time (< 500ms)."""
        latencies = []

        payload = {
            "z_valence": 1,
            "concentration_out_molar": 5e-3,
            "concentration_in_molar": 140e-3,
            "temperature_k": 310.0,
        }

        for _ in range(5):
            start = time.perf_counter()
            response = perf_client.post("/nernst", json=payload)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            assert response.status_code == 200

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # Nernst should be fast (just math)
        assert avg_latency < 500, f"Avg latency {avg_latency:.2f}ms exceeds 500ms"
        assert p95_latency < 1000, f"P95 latency {p95_latency:.2f}ms exceeds 1000ms"

    def test_simulate_small_grid_latency(self, perf_client: TestClient) -> None:
        """Simulate endpoint with small grid should complete reasonably (< 5s)."""
        payload = {
            "seed": 42,
            "grid_size": 32,
            "steps": 32,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        start = time.perf_counter()
        response = perf_client.post("/simulate", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert latency_ms < 5000, f"Simulate latency {latency_ms:.2f}ms exceeds 5s"

    def test_validate_minimal_latency(self, perf_client: TestClient) -> None:
        """Validate endpoint with minimal params should complete (< 10s)."""
        pytest.importorskip("torch")
        payload = {
            "seed": 42,
            "epochs": 1,
            "batch_size": 4,
            "grid_size": 32,
            "steps": 32,
        }

        start = time.perf_counter()
        response = perf_client.post("/validate", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert latency_ms < 10000, f"Validate latency {latency_ms:.2f}ms exceeds 10s"


class TestAPIThroughput:
    """Throughput tests for API endpoints."""

    def test_health_throughput(self, perf_client: TestClient) -> None:
        """Health endpoint should handle multiple requests."""
        num_requests = 50
        start = time.perf_counter()

        success_count = 0
        for _ in range(num_requests):
            response = perf_client.get("/health")
            if response.status_code == 200:
                success_count += 1

        total_time = time.perf_counter() - start
        rps = num_requests / total_time

        # All requests should succeed
        assert success_count == num_requests
        # Should achieve reasonable throughput
        assert rps > 10, f"Throughput {rps:.2f} RPS below 10 RPS"

    def test_nernst_throughput(self, perf_client: TestClient) -> None:
        """Nernst endpoint should handle multiple sequential requests."""
        num_requests = 20
        payload = {
            "z_valence": 1,
            "concentration_out_molar": 5e-3,
            "concentration_in_molar": 140e-3,
            "temperature_k": 310.0,
        }

        start = time.perf_counter()

        success_count = 0
        for _ in range(num_requests):
            response = perf_client.post("/nernst", json=payload)
            if response.status_code == 200:
                success_count += 1

        total_time = time.perf_counter() - start
        rps = num_requests / total_time

        # All requests should succeed
        assert success_count == num_requests
        # Should achieve reasonable throughput
        assert rps > 5, f"Throughput {rps:.2f} RPS below 5 RPS"


class TestAPIErrorRates:
    """Error rate tests for API."""

    def test_zero_error_rate_valid_requests(self, perf_client: TestClient) -> None:
        """Valid requests should have 0% error rate."""
        num_requests = 30
        errors = 0

        for _ in range(num_requests):
            response = perf_client.get("/health")
            if response.status_code != 200:
                errors += 1

        error_rate = errors / num_requests
        assert error_rate == 0, f"Error rate {error_rate:.2%} is not 0%"

    def test_nernst_consistency(self, perf_client: TestClient) -> None:
        """Nernst endpoint should return consistent results."""
        payload = {
            "z_valence": 1,
            "concentration_out_molar": 5e-3,
            "concentration_in_molar": 140e-3,
            "temperature_k": 310.0,
        }

        results = []
        for _ in range(10):
            response = perf_client.post("/nernst", json=payload)
            assert response.status_code == 200
            results.append(response.json()["potential_mV"])

        # All results should be identical (deterministic)
        assert len(set(results)) == 1, "Nernst results are not consistent"


class TestAPIStress:
    """Light stress tests for API."""

    def test_rapid_fire_requests(self, perf_client: TestClient) -> None:
        """API should handle rapid sequential requests without errors."""
        num_requests = 100
        errors = 0

        for _ in range(num_requests):
            response = perf_client.get("/health")
            if response.status_code != 200:
                errors += 1

        error_rate = errors / num_requests
        assert error_rate < 0.01, f"Error rate {error_rate:.2%} exceeds 1%"

    def test_mixed_endpoint_load(self, perf_client: TestClient) -> None:
        """API should handle mixed endpoint requests."""
        payloads = [
            ("GET", "/health", None),
            (
                "POST",
                "/nernst",
                {
                    "z_valence": 1,
                    "concentration_out_molar": 5e-3,
                    "concentration_in_molar": 140e-3,
                },
            ),
            ("GET", get_api_config().metrics.endpoint, None),
        ]

        errors = 0
        for _ in range(20):
            for method, path, body in payloads:
                if method == "GET":
                    response = perf_client.get(path)
                else:
                    response = perf_client.post(path, json=body)

                # All payloads above are valid, expect 200 for all
                if response.status_code != 200:
                    errors += 1

        total_requests = 20 * len(payloads)
        error_rate = errors / total_requests
        assert error_rate < 0.01, f"Error rate {error_rate:.2%} exceeds 1%"
