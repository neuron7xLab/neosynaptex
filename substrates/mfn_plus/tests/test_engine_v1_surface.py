from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

import mycelium_fractal_net as mfn
from mycelium_fractal_net.api import app

if TYPE_CHECKING:
    from pathlib import Path


def test_sdk_surface_end_to_end(tmp_path: Path) -> None:
    spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
    seq = mfn.simulate(spec)
    desc = mfn.extract(seq)
    det = mfn.detect(seq)
    fc = mfn.forecast(seq, horizon=4)
    rep = mfn.report(seq, output_root=str(tmp_path), horizon=4)

    assert seq.has_history
    assert len(desc.embedding) > 10
    assert det.label in {"nominal", "watch", "anomalous"}
    assert fc.horizon == 4
    assert (tmp_path / rep.run_id / "report.md").exists()


def test_api_v1_surface_end_to_end(tmp_path: Path) -> None:
    client = TestClient(app)
    sim = client.post("/v1/simulate", json={"grid_size": 16, "steps": 8, "with_history": True})
    assert sim.status_code == 200
    payload = sim.json()

    extract = client.post("/v1/extract", json={"history": payload["history"]})
    detect = client.post("/v1/detect", json={"history": payload["history"]})
    forecast = client.post("/v1/forecast", json={"history": payload["history"], "horizon": 4})
    compare = client.post(
        "/v1/compare",
        json={
            "left": {"history": payload["history"]},
            "right": {"history": payload["history"]},
        },
    )
    report = client.post(
        "/v1/report",
        json={
            "history": payload["history"],
            "horizon": 4,
            "output_root": str(tmp_path),
        },
    )

    assert extract.status_code == 200
    assert detect.status_code == 200
    assert forecast.status_code == 200
    assert compare.status_code == 200
    assert report.status_code == 200
    assert report.json()["run_id"].startswith("run_")
