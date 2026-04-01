from __future__ import annotations

import json

import mycelium_fractal_net as mfn


def test_report_writes_visual_artifacts_and_optional_manifest(tmp_path) -> None:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
    report = mfn.report(seq, output_root=str(tmp_path), horizon=4)
    run_dir = tmp_path / report.run_id
    for name in [
        "report.html",
        "field.svg",
        "history_mean.svg",
        "forecast_final.svg",
        "comparison_delta.svg",
        "trajectory.svg",
        "summary.json",
    ]:
        assert (run_dir / name).exists(), name
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["optional_artifact_list"]) >= {
        "report.html",
        "field.svg",
        "trajectory.svg",
    }
    assert manifest["optional_artifact_manifest"]["report.html"]["sha256"]
