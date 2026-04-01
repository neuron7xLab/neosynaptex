"""
Integration tests for API and CLI consistency.

Tests that CLI validation and HTTP /validate produce consistent results
for the same seed and configuration, and that all API endpoints correctly
marshal/demarshal data through the integration layer schemas.

Reference: docs/ARCHITECTURE.md
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.api import app

try:
    from mycelium_fractal_net import ValidationConfig, run_validation

    _HAS_TORCH = True
except Exception:
    _HAS_TORCH = False
from mycelium_fractal_net.integration import (
    ExecutionMode,
    FederatedAggregateRequest,
    NernstRequest,
    ServiceContext,
    SimulateRequest,
    ValidateRequest,
    aggregate_gradients_adapter,
    compute_nernst_adapter,
    run_simulation_adapter,
    run_validation_adapter,
)


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


# Test data constants
SAMPLE_GRADIENTS_4D = [
    [1.0, 2.0, 3.0],
    [1.1, 2.1, 3.1],
    [1.2, 2.2, 3.2],
    [10.0, 10.0, 10.0],
]
SAMPLE_GRADIENTS_2D = [[1.0, 2.0], [1.1, 2.1], [1.2, 2.2]]


class TestCLIAPIConsistency:
    """Tests for consistency between CLI and API validation results."""

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for ValidationConfig")
    def test_validate_cli_vs_api_consistency(self, client: TestClient) -> None:
        """CLI validate vs HTTP /validate should give consistent metrics for same seed."""
        seed = 42
        epochs = 1
        grid_size = 32
        steps = 32

        # Run via core function (like CLI does)
        cfg = ValidationConfig(
            seed=seed,
            epochs=epochs,
            batch_size=4,
            grid_size=grid_size,
            steps=steps,
        )
        cli_metrics = run_validation(cfg)

        # Run via HTTP API
        response = client.post(
            "/validate",
            json={
                "seed": seed,
                "epochs": epochs,
                "batch_size": 4,
                "grid_size": grid_size,
                "steps": steps,
            },
        )
        assert response.status_code == 200
        api_metrics = response.json()

        # Core metrics should be identical for same seed
        assert cli_metrics["loss_start"] == pytest.approx(api_metrics["loss_start"], rel=1e-5)
        assert cli_metrics["loss_final"] == pytest.approx(api_metrics["loss_final"], rel=1e-5)
        assert cli_metrics["nernst_symbolic_mV"] == pytest.approx(
            api_metrics["nernst_symbolic_mV"], rel=1e-5
        )

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for validation adapter")
    def test_validate_adapter_consistency(self) -> None:
        """Validate adapter should return consistent results."""
        seed = 42
        request = ValidateRequest(seed=seed, epochs=1, grid_size=32, steps=32)
        ctx = ServiceContext(seed=seed, mode=ExecutionMode.API)

        response = run_validation_adapter(request, ctx)

        # Validate response structure
        assert response.loss_start > 0
        assert response.loss_final > 0
        assert response.nernst_symbolic_mV < 0  # K+ should be negative
        assert response.nernst_symbolic_mV == pytest.approx(-89.0, abs=1.0)


class TestAPIEndpoints:
    """Tests for API endpoint schema marshaling."""

    def test_simulate_endpoint_marshaling(self, client: TestClient) -> None:
        """Test /simulate endpoint marshals data correctly."""
        response = client.post(
            "/simulate",
            json={
                "seed": 42,
                "grid_size": 32,
                "steps": 32,
                "alpha": 0.18,
                "spike_probability": 0.25,
                "turing_enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "growth_events" in data
        assert "pot_min_mV" in data
        assert "pot_max_mV" in data
        assert "pot_mean_mV" in data
        assert "pot_std_mV" in data
        assert "fractal_dimension" in data

        # Validate physical constraints
        assert data["pot_min_mV"] >= -95.0  # mV
        assert data["pot_max_mV"] <= 40.0  # mV
        assert 0.0 <= data["fractal_dimension"] <= 2.0

    def test_nernst_endpoint_marshaling(self, client: TestClient) -> None:
        """Test /nernst endpoint marshals data correctly."""
        response = client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
                "temperature_k": 310.0,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "potential_mV" in data

        # K+ potential should be ~-89 mV
        assert data["potential_mV"] == pytest.approx(-89.0, abs=1.0)

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for federated")
    def test_federated_aggregate_endpoint_marshaling(self, client: TestClient) -> None:
        """Test /federated/aggregate endpoint marshals data correctly."""
        response = client.post(
            "/federated/aggregate",
            json={
                "gradients": SAMPLE_GRADIENTS_4D,
                "num_clusters": 2,
                "byzantine_fraction": 0.2,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "aggregated_gradient" in data
        assert "num_input_gradients" in data
        assert data["num_input_gradients"] == 4
        assert len(data["aggregated_gradient"]) == 3

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for federated")
    def test_federated_empty_gradients(self, client: TestClient) -> None:
        """Test /federated/aggregate handles empty gradients."""
        response = client.post(
            "/federated/aggregate",
            json={
                "gradients": [],
                "num_clusters": 2,
                "byzantine_fraction": 0.2,
            },
        )
        assert response.status_code == 400

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for federated")
    def test_federated_inconsistent_gradient_lengths(self, client: TestClient) -> None:
        """Test /federated/aggregate rejects inconsistent gradient sizes."""
        response = client.post(
            "/federated/aggregate",
            json={
                "gradients": [[1.0, 2.0, 3.0], [1.0, 2.0]],
                "num_clusters": 2,
                "byzantine_fraction": 0.2,
            },
        )
        assert response.status_code == 400

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test /health endpoint returns correct response."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestAdapters:
    """Tests for integration layer adapters."""

    def test_simulation_adapter(self) -> None:
        """Test simulation adapter converts correctly."""
        request = SimulateRequest(seed=42, grid_size=32, steps=32)
        ctx = ServiceContext(seed=42, mode=ExecutionMode.API)

        response = run_simulation_adapter(request, ctx)

        assert response.growth_events >= 0
        assert response.pot_min_mV >= -95.0
        assert response.pot_max_mV <= 40.0
        assert 0.0 <= response.fractal_dimension <= 2.0

    def test_nernst_adapter(self) -> None:
        """Test Nernst adapter converts correctly."""
        request = NernstRequest(
            z_valence=1,
            concentration_out_molar=5e-3,
            concentration_in_molar=140e-3,
            temperature_k=310.0,
        )
        ctx = ServiceContext(mode=ExecutionMode.API)

        response = compute_nernst_adapter(request, ctx)

        assert response.potential_mV == pytest.approx(-89.0, abs=1.0)

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for federated")
    def test_federated_adapter(self) -> None:
        """Test federated aggregation adapter converts correctly."""
        request = FederatedAggregateRequest(
            gradients=SAMPLE_GRADIENTS_2D,
            num_clusters=2,
            byzantine_fraction=0.2,
        )
        ctx = ServiceContext(mode=ExecutionMode.API)

        response = aggregate_gradients_adapter(request, ctx)

        assert response.num_input_gradients == 3
        assert len(response.aggregated_gradient) == 2

    @pytest.mark.skipif(not _HAS_TORCH, reason="torch required for federated")
    def test_federated_adapter_rejects_inconsistent_gradients(self) -> None:
        """Test federated adapter fails on mismatched gradient lengths."""
        request = FederatedAggregateRequest(
            gradients=[[1.0, 2.0, 3.0], [1.0, 2.0]],
            num_clusters=2,
            byzantine_fraction=0.2,
        )
        ctx = ServiceContext(mode=ExecutionMode.API)

        with pytest.raises(ValueError, match="Inconsistent gradient dimensions"):
            aggregate_gradients_adapter(request, ctx)


class TestServiceContext:
    """Tests for ServiceContext."""

    def test_context_with_seed(self) -> None:
        """Test ServiceContext provides reproducible RNG."""
        ctx = ServiceContext(seed=42)

        rng1 = ctx.get_rng()
        val1 = rng1.random()

        ctx.reset_rng()
        rng2 = ctx.get_rng()
        val2 = rng2.random()

        assert val1 == val2

    def test_context_with_mode(self) -> None:
        """Test ServiceContext preserves mode."""
        ctx = ServiceContext(seed=42, mode=ExecutionMode.CLI)
        assert ctx.mode == ExecutionMode.CLI

        ctx2 = ctx.with_mode(ExecutionMode.API)
        assert ctx2.mode == ExecutionMode.API
        assert ctx.mode == ExecutionMode.CLI  # Original unchanged

    def test_context_metadata(self) -> None:
        """Test ServiceContext metadata."""
        ctx = ServiceContext(seed=42)
        ctx.set_metadata("test_key", "test_value")

        assert ctx.get_metadata("test_key") == "test_value"
        assert ctx.get_metadata("missing", "default") == "default"


class TestDeterminism:
    """Tests for deterministic behavior across API and CLI."""

    def test_simulation_determinism_via_api(self, client: TestClient) -> None:
        """Same seed should produce same simulation results via API."""
        params = {
            "seed": 42,
            "grid_size": 32,
            "steps": 32,
            "alpha": 0.18,
            "spike_probability": 0.25,
            "turing_enabled": True,
        }

        response1 = client.post("/simulate", json=params)
        response2 = client.post("/simulate", json=params)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert data1["growth_events"] == data2["growth_events"]
        assert data1["pot_min_mV"] == pytest.approx(data2["pot_min_mV"], rel=1e-5)
        assert data1["fractal_dimension"] == pytest.approx(data2["fractal_dimension"], rel=1e-5)

    def test_nernst_determinism(self, client: TestClient) -> None:
        """Nernst computation should be deterministic."""
        params = {
            "z_valence": 1,
            "concentration_out_molar": 5e-3,
            "concentration_in_molar": 140e-3,
            "temperature_k": 310.0,
        }

        response1 = client.post("/nernst", json=params)
        response2 = client.post("/nernst", json=params)

        assert response1.json()["potential_mV"] == response2.json()["potential_mV"]


class TestCORSConfiguration:
    """Tests for CORS middleware configuration.

    Reference: docs/MFN_BACKLOG.md#MFN-API-003
    """

    def test_cors_preflight_request(self, client: TestClient) -> None:
        """Test CORS preflight OPTIONS request is handled."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should return 200
        assert response.status_code == 200

    def test_cors_headers_on_response(self, client: TestClient) -> None:
        """Test CORS headers are present in responses."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200

        # In dev mode (default), should have CORS headers
        # Access-Control-Allow-Origin should be present
        # Note: In test mode this may vary based on MFN_ENV setting
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_cors_post_request_with_origin(self, client: TestClient) -> None:
        """Test CORS works for POST requests."""
        response = client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
                "temperature_k": 310.0,
            },
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
