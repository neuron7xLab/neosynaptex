from __future__ import annotations

from pathlib import Path

from mycelium_fractal_net.pipelines.scenarios import run_canonical_scenarios


def test_run_canonical_scenarios(tmp_path: Path) -> None:
    results = run_canonical_scenarios(tmp_path)
    assert set(results) == {
        "synthetic_morphology",
        "sensor_grid_anomaly",
        "regime_transition",
    }
    for payload in results.values():
        assert Path(payload["dataset"]).exists()
        assert Path(payload["expected_results"]).exists()
        assert Path(payload["reference_report"]).exists()
