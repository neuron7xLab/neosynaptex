from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from mycelium_fractal_net.core.detect import detect_regime_shift
from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.pipelines.reporting import build_analysis_report


def run(output_root: str | Path = "artifacts/scenarios") -> dict[str, str]:
    root = Path(output_root)
    dataset_dir = root / "regime_transition"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    sequence = simulate_scenario("regime_transition")
    regime = detect_regime_shift(sequence)
    report = build_analysis_report(sequence, output_root=root / "runs", horizon=8)
    dataset_path = dataset_dir / "regime_transition_history.npy"
    np.save(
        dataset_path,
        (sequence.history if sequence.history is not None else sequence.field[None, :, :]),
    )
    expected = {
        "scenario": "regime_transition",
        "regime_label": regime.label,
        "regime_score": regime.score,
        "report_run_id": report.run_id,
    }
    expected_path = dataset_dir / "expected_results.json"
    expected_path.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    example_cli_path = dataset_dir / "example_cli.txt"
    example_cli_path.write_text(
        "mfn forecast --input-npy artifacts/scenarios/regime_transition/regime_transition_history.npy --horizon 8\n",
        encoding="utf-8",
    )
    manifest_path = dataset_dir / "scenario_manifest.json"
    manifest = {
        "scenario": "regime_transition",
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
