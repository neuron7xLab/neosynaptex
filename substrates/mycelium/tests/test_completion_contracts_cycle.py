from __future__ import annotations

import json

import mycelium_fractal_net as mfn


def test_detection_payload_aliases() -> None:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
    payload = mfn.detect(seq).to_dict()
    assert payload["top_contributing_features"] == payload["contributing_features"]
    assert "evidence" in payload


def test_comparison_payload_aliases() -> None:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
    payload = mfn.compare(seq, seq).to_dict()
    assert payload["morphology_distance"] == payload["distance"]
    assert payload["nearest_structural_analog"] in {
        "self-similar",
        "reference-family",
        "no-close-analog",
    }


def test_manifest_contains_fingerprints(tmp_path) -> None:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
    report = mfn.report(seq, output_root=str(tmp_path), horizon=4)
    manifest = json.loads((tmp_path / report.run_id / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "mfn-artifact-manifest-v2"
    assert "artifact_manifest" in manifest
    assert manifest["artifact_manifest"]["comparison.json"]["sha256"]
    assert manifest["artifact_manifest"]["config.json"]["bytes"] > 0
