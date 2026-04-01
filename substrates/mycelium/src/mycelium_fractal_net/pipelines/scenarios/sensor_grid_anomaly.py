from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from mycelium_fractal_net.core.detect import detect_anomaly, detect_morphology_drift
from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.pipelines.reporting import build_analysis_report


def run(output_root: str | Path = "artifacts/scenarios") -> dict[str, str]:
    root = Path(output_root)
    dataset_dir = root / "sensor_grid_anomaly"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    baseline = simulate_scenario("synthetic_morphology")
    anomaly = simulate_scenario("sensor_grid_anomaly")
    detection = detect_anomaly(anomaly)
    drift = detect_morphology_drift(baseline, anomaly)
    report = build_analysis_report(
        anomaly, output_root=root / "runs", horizon=6, comparison_sequence=baseline
    )
    dataset_path = dataset_dir / "sensor_grid_history.npy"
    np.save(
        dataset_path,
        anomaly.history if anomaly.history is not None else anomaly.field[None, :, :],
    )
    expected = {
        "scenario": "sensor_grid_anomaly",
        "anomaly_label": detection.label,
        "anomaly_score": detection.score,
        "drift_score": drift["normalized_distance"],
        "report_run_id": report.run_id,
    }
    expected_path = dataset_dir / "expected_results.json"
    expected_path.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    example_cli_path = dataset_dir / "example_cli.txt"
    example_cli_path.write_text(
        "mfn detect --input-npy artifacts/scenarios/sensor_grid_anomaly/sensor_grid_history.npy\n",
        encoding="utf-8",
    )
    manifest_path = dataset_dir / "scenario_manifest.json"
    manifest = {
        "scenario": "sensor_grid_anomaly",
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
