"""
Locust load test scenarios for MyceliumFractalNet API.

Provides load testing scenarios for API endpoints with configurable
concurrency and authentication.

Usage:
    # Run locally (requires API server running)
    locust -f load_tests/locustfile.py --host http://localhost:8000

    # Run with web UI
    locust -f load_tests/locustfile.py --host http://localhost:8000 --web-host 0.0.0.0

    # Run headless with specific users and spawn rate
    locust -f load_tests/locustfile.py --host http://localhost:8000 \
        --headless -u 10 -r 2 -t 1m

Environment Variables:
    MFN_LOADTEST_BASE_URL  - API base URL (default: http://localhost:8000)
    MFN_LOADTEST_API_KEY   - API key for authentication (optional)
    MFN_LOADTEST_DURATION  - Test duration in seconds (for automated runs)

Reference: docs/MFN_BACKLOG.md#MFN-TEST-001
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, between, task


class MFNAPIUser(HttpUser):
    """
    Simulated user for MFN API load testing.

    Performs a mix of API operations with realistic wait times.
    """

    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")

    def _get_headers(self) -> dict:
        """Get headers including API key if configured."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @task(10)
    def health_check(self) -> None:
        """
        Check API health.

        High frequency task - used for availability monitoring.
        """
        self.client.get("/health", name="/health")

    @task(5)
    def compute_nernst(self) -> None:
        """
        Compute Nernst potential.

        Lightweight computation - medium frequency.
        """
        # Randomize ion parameters for variety
        ions = [
            {"z": 1, "out": 5e-3, "in": 140e-3},  # K+
            {"z": 1, "out": 145e-3, "in": 12e-3},  # Na+
            {"z": 2, "out": 2e-3, "in": 0.1e-6},  # Ca2+
        ]
        ion = random.choice(ions)

        payload = {
            "z_valence": ion["z"],
            "concentration_out_molar": ion["out"],
            "concentration_in_molar": ion["in"],
            "temperature_k": 310.0,
        }

        self.client.post(
            "/nernst",
            json=payload,
            headers=self._get_headers(),
            name="/nernst",
        )

    @task(2)
    def simulate_small(self) -> None:
        """
        Run small simulation.

        More expensive - lower frequency.
        """
        payload = {
            "seed": random.randint(0, 10000),
            "grid_size": 32,
            "steps": 32,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        self.client.post(
            "/simulate",
            json=payload,
            headers=self._get_headers(),
            name="/simulate (32x32)",
        )

    @task(1)
    def simulate_medium(self) -> None:
        """
        Run medium simulation.

        Expensive - low frequency.
        """
        payload = {
            "seed": random.randint(0, 10000),
            "grid_size": 64,
            "steps": 64,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        self.client.post(
            "/simulate",
            json=payload,
            headers=self._get_headers(),
            name="/simulate (64x64)",
        )

    @task(1)
    def validate_minimal(self) -> None:
        """
        Run minimal validation.

        Most expensive - very low frequency.
        """
        payload = {
            "seed": random.randint(0, 10000),
            "epochs": 1,
            "batch_size": 4,
            "grid_size": 32,
            "steps": 32,
        }

        self.client.post(
            "/validate",
            json=payload,
            headers=self._get_headers(),
            name="/validate",
        )

    @task(3)
    def federated_aggregate(self) -> None:
        """
        Run federated aggregation.

        Medium cost - medium frequency.
        """
        # Generate random gradients
        num_clients = random.randint(3, 10)
        gradient_dim = random.randint(3, 20)

        gradients = [[random.gauss(0, 1) for _ in range(gradient_dim)] for _ in range(num_clients)]

        payload = {
            "gradients": gradients,
            "num_clusters": min(num_clients // 2, 5),
            "byzantine_fraction": 0.2,
        }

        self.client.post(
            "/federated/aggregate",
            json=payload,
            headers=self._get_headers(),
            name="/federated/aggregate",
        )

    @task(5)
    def get_metrics(self) -> None:
        """
        Fetch Prometheus metrics.

        Medium frequency - monitoring simulation.
        """
        self.client.get("/metrics", name="/metrics")


class MFNReadOnlyUser(HttpUser):
    """
    Read-only user for light load testing.

    Only performs GET operations - useful for testing read path.
    """

    wait_time = between(0.5, 2)

    @task(5)
    def health_check(self) -> None:
        """Check API health."""
        self.client.get("/health", name="/health (readonly)")

    @task(3)
    def get_metrics(self) -> None:
        """Fetch metrics."""
        self.client.get("/metrics", name="/metrics (readonly)")


class MFNHeavyUser(HttpUser):
    """
    Heavy computation user for stress testing.

    Focuses on expensive operations.
    """

    wait_time = between(2, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @task(3)
    def simulate_medium(self) -> None:
        """Run medium simulation."""
        payload = {
            "seed": random.randint(0, 10000),
            "grid_size": 64,
            "steps": 64,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        self.client.post(
            "/simulate",
            json=payload,
            headers=self._get_headers(),
            name="/simulate (heavy)",
        )

    @task(1)
    def validate_full(self) -> None:
        """Run validation with more epochs."""
        payload = {
            "seed": random.randint(0, 10000),
            "epochs": 2,
            "batch_size": 8,
            "grid_size": 48,
            "steps": 48,
        }

        self.client.post(
            "/validate",
            json=payload,
            headers=self._get_headers(),
            name="/validate (heavy)",
        )


class MFNStressUser(HttpUser):
    """
    Stress test user with large payloads and high-frequency requests.

    Designed to test system limits and identify breaking points.
    Use sparingly - high resource consumption.
    """

    wait_time = between(0.5, 2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @task(2)
    def simulate_large_grid(self) -> None:
        """Run large grid simulation (128x128)."""
        payload = {
            "seed": random.randint(0, 10000),
            "grid_size": 128,
            "steps": 100,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        self.client.post(
            "/simulate",
            json=payload,
            headers=self._get_headers(),
            name="/simulate (128x128 stress)",
        )

    @task(1)
    def federated_large(self) -> None:
        """Run large federated aggregation."""
        num_clients = 50
        gradient_dim = 100

        gradients = [[random.gauss(0, 1) for _ in range(gradient_dim)] for _ in range(num_clients)]

        payload = {
            "gradients": gradients,
            "num_clusters": 10,
            "byzantine_fraction": 0.2,
        }

        self.client.post(
            "/federated/aggregate",
            json=payload,
            headers=self._get_headers(),
            name="/federated/aggregate (stress)",
        )

    @task(3)
    def nernst_burst(self) -> None:
        """Burst of Nernst calculations."""
        ions = [
            {"z": 1, "out": 5e-3, "in": 140e-3},
            {"z": 1, "out": 145e-3, "in": 12e-3},
            {"z": 2, "out": 2e-3, "in": 0.1e-6},
            {"z": -1, "out": 120e-3, "in": 4e-3},
        ]

        for ion in ions:
            payload = {
                "z_valence": ion["z"],
                "concentration_out_molar": ion["out"],
                "concentration_in_molar": ion["in"],
                "temperature_k": random.uniform(300, 315),
            }
            self.client.post(
                "/nernst",
                json=payload,
                headers=self._get_headers(),
                name="/nernst (burst)",
            )


class MFNScalabilityUser(HttpUser):
    """
    Scalability test user with increasing load patterns.

    Tests system behavior as load increases.
    """

    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("MFN_LOADTEST_API_KEY", "")
        self._request_count = 0

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    @task(5)
    def simulate_varying_load(self) -> None:
        """Simulate with varying grid sizes based on request count."""
        self._request_count += 1

        # Cycle through grid sizes: 32 -> 64 -> 128 -> 32 ...
        grid_sizes = [32, 48, 64, 96]
        grid_size = grid_sizes[self._request_count % len(grid_sizes)]

        payload = {
            "seed": random.randint(0, 10000),
            "grid_size": grid_size,
            "steps": 50,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        self.client.post(
            "/simulate",
            json=payload,
            headers=self._get_headers(),
            name=f"/simulate ({grid_size}x{grid_size} scale)",
        )

    @task(3)
    def health_check_rapid(self) -> None:
        """Rapid health checks for availability monitoring."""
        for _ in range(5):
            self.client.get("/health", name="/health (rapid)")

    @task(2)
    def metrics_monitoring(self) -> None:
        """Metrics fetch for monitoring scalability."""
        self.client.get("/metrics", name="/metrics (scale)")
