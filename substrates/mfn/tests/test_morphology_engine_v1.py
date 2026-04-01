from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

import mycelium_fractal_net as mfn
from mycelium_fractal_net.api import app

if TYPE_CHECKING:
    from pathlib import Path


def test_public_root_exports() -> None:
    import pytest

    assert mfn.__version__ == "0.1.0"
    try:
        assert mfn.SimulationConfig is not None
        assert mfn.SimulationResult is not None
    except ImportError:
        pytest.skip("Torch-dependent exports (SimulationConfig/SimulationResult) unavailable")
    assert mfn.BODY_TEMPERATURE_K == 310.0


def test_report_manifest_roundtrip(tmp_path: Path) -> None:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=10, seed=42))
    report = mfn.report(seq, output_root=str(tmp_path), horizon=4)
    manifest = tmp_path / report.run_id / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["run_id"] == report.run_id
    assert (tmp_path / report.run_id / "report.md").exists()


def test_api_v1_report_surface(tmp_path: Path) -> None:
    client = TestClient(app)
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
    assert "descriptor" in payload
    assert "detection" in payload
    assert "forecast" in payload
