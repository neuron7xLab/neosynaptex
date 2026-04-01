"""Improvement cycle."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import mycelium_fractal_net as mfn
from mycelium_fractal_net.integration.api_server import create_app


def main() -> None:
    out_root = Path("artifacts/cycle")
    out_root.mkdir(parents=True, exist_ok=True)
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
    descriptor = mfn.extract(seq)
    detection = mfn.detect(seq)
    forecast = mfn.forecast(seq, horizon=4)
    comparison = mfn.compare(seq, seq)
    report = mfn.report(seq, output_root=str(out_root), horizon=4)
    client = TestClient(create_app())
    health = client.get("/health").json()
    payload = {
        "descriptor_version": descriptor.version,
        "detection_label": detection.label,
        "forecast_method": forecast.method,
        "comparison_label": comparison.label,
        "report_run_id": report.run_id,
        "health": health,
    }
    (out_root / "cycle_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
