from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _module_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(Path("src").resolve())
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_path
    )
    return env


def test_scaled_sleep_stack_module_smoke(tmp_path: Path) -> None:
    out_dir = tmp_path / "scaled"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.tools.run_scaled_sleep_stack",
            "--out",
            str(out_dir),
            "--seed",
            "42",
            "--n",
            "80",
            "--steps-wake",
            "30",
            "--steps-sleep",
            "30",
            "--baseline-steps-wake",
            "20",
            "--baseline-steps-sleep",
            "10",
            "--determinism-runs",
            "1",
            "--equivalence-steps-wake",
            "20",
            "--skip-backend-equivalence",
            "--skip-baseline",
            "--no-raster",
            "--no-plots",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_module_env(),
    )
    assert proc.returncode == 0

    manifest_path = out_dir / "scaled_run1" / "manifest.json"
    metrics_path = out_dir / "scaled_run1" / "metrics.json"
    assert manifest_path.exists()
    assert metrics_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["seed"] == 42
    assert manifest["N"] == 80
    assert manifest["steps_wake"] == 30
    assert manifest["steps_sleep"] == 30

    metrics = json.loads(metrics_path.read_text())
    assert "backend" in metrics

    summary_path = out_dir / "metrics.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["seed"] == 42
    required_summary_keys = {
        "seed",
        "N_scaled",
        "steps_wake_scaled",
        "steps_sleep_scaled",
        "determinism_runs",
        "backend_equivalence",
    }
    assert required_summary_keys <= set(summary)
    assert summary["N_scaled"] == 80
    assert summary["steps_wake_scaled"] == 30
    assert summary["steps_sleep_scaled"] == 30
    assert summary["determinism_runs"] == 1
    assert summary["determinism_identical"] is None
    assert summary["backend_equivalence"]["skipped"] is True
    assert summary["baseline_skipped"] is True
    assert summary["baseline"] is None
