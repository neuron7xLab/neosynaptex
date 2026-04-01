from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.pipelines.reporting import build_analysis_report


def run(output_root: str | Path = "artifacts/scenarios") -> dict[str, str]:
    root = Path(output_root)
    dataset_dir = root / "synthetic_morphology"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    sequence = simulate_scenario("synthetic_morphology")
    descriptor = compute_morphology_descriptor(sequence)
    report = build_analysis_report(sequence, output_root=root / "runs", horizon=6)
    dataset_path = dataset_dir / "field_history.npy"
    np.save(
        dataset_path,
        (sequence.history if sequence.history is not None else sequence.field[None, :, :]),
    )
    expected = {
        "scenario": "synthetic_morphology",
        "descriptor_version": descriptor.version,
        "fractal_dimension": descriptor.features.get("D_box", 0.0),
        "report_run_id": report.run_id,
    }
    expected_path = dataset_dir / "expected_results.json"
    expected_path.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    example_cli_path = dataset_dir / "example_cli.txt"
    example_cli_path.write_text(
        "mfn report --grid-size 32 --steps 24 --horizon 6 --output-root artifacts/runs\n",
        encoding="utf-8",
    )
    manifest_path = dataset_dir / "scenario_manifest.json"
    manifest = {
        "scenario": "synthetic_morphology",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "expected_results": str(expected_path),
        "example_cli": str(example_cli_path),
        "reference_report": str((root / "runs" / report.run_id).resolve()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
