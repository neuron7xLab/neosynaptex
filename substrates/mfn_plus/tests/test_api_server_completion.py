from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from mycelium_fractal_net.integration.api_server import create_app

if TYPE_CHECKING:
    from pathlib import Path


def test_api_server_health_and_metrics() -> None:
    client = TestClient(create_app())
    payload = client.get("/health").json()
    assert payload["status"] == "healthy"
    assert payload["engine_version"] == "0.1.0"
    assert payload["api_version"] == "v1"
    assert payload["uptime"] >= 0.0
    client.post("/v1/simulate", json={"grid_size": 16, "steps": 8, "with_history": True})
    body = client.get("/metrics").json()
    assert body["simulation_requests"] >= 1
    assert "runtime_latency" in body


def test_api_server_report_creates_comparison_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/report",
        json={
            "spec": {"grid_size": 16, "steps": 8, "with_history": True},
            "horizon": 4,
            "output_root": str(tmp_path),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    run_dir = tmp_path / payload["run_id"]
    assert (run_dir / "comparison.json").exists()
    assert (run_dir / "manifest.json").exists()
