from __future__ import annotations

import json

import mycelium_fractal_net as mfn


def test_manifest_and_required_artifacts(tmp_path) -> None:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
    report = mfn.report(seq, output_root=str(tmp_path), horizon=4)
    run_dir = tmp_path / report.run_id
    required = {
        "config.json",
        "field.npy",
        "history.npy",
        "descriptor.json",
        "detection.json",
        "forecast.json",
        "comparison.json",
        "report.md",
        "manifest.json",
        "causal_validation.json",
    }
    on_disk = {p.name for p in run_dir.iterdir()}
    assert required.issubset(on_disk), f"Missing: {required - on_disk}"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == report.run_id
    assert required == set(manifest["artifact_list"])

    # Verify causal validation passed
    causal = json.loads((run_dir / "causal_validation.json").read_text(encoding="utf-8"))
    assert causal["ok"] is True
    assert causal["decision"] in ("pass", "degraded")
    assert causal["error_count"] == 0
