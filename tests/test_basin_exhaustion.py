from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_small_grid_completes_without_error(tmp_path: Path):
    out_dir = tmp_path / "basin"
    cmd = [
        sys.executable,
        "scripts/basin_exhaustion.py",
        "--grid",
        "11x11x11",
        "--steps",
        "80",
        "--seeds",
        "1",
        "--fault-rates",
        "0.05",
        "--sigmas",
        "0.02",
        "--rhos",
        "0.005",
        "--epsilons",
        "0.03",
        "--etas",
        "0.05",
        "--chi-mins",
        "0.3",
        "--output",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert (out_dir / "basin_summary.json").exists()


def test_small_grid_unresolved_fraction_under_5pct(tmp_path: Path):
    out_dir = tmp_path / "basin2"
    cmd = [
        sys.executable,
        "scripts/basin_exhaustion.py",
        "--grid",
        "11x11x11",
        "--steps",
        "400",
        "--seeds",
        "1",
        "--fault-rates",
        "0.05",
        "--sigmas",
        "0.02",
        "--rhos",
        "0.005",
        "--epsilons",
        "0.03",
        "--etas",
        "0.05",
        "--chi-mins",
        "0.3",
        "--output",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads((out_dir / "basin_summary.json").read_text(encoding="utf-8"))
    assert payload["mean_unresolved_fraction"] < 0.05


def test_output_json_is_valid(tmp_path: Path):
    out_dir = tmp_path / "basin3"
    cmd = [
        sys.executable,
        "scripts/basin_exhaustion.py",
        "--grid",
        "11x11x11",
        "--steps",
        "50",
        "--seeds",
        "1",
        "--fault-rates",
        "0.05",
        "--sigmas",
        "0.02",
        "--rhos",
        "0.005",
        "--epsilons",
        "0.03",
        "--etas",
        "0.05",
        "--chi-mins",
        "0.3",
        "--output",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    summary = json.loads((out_dir / "basin_summary.json").read_text(encoding="utf-8"))
    runs = json.loads((out_dir / "basin_runs.json").read_text(encoding="utf-8"))
    assert isinstance(summary, dict)
    assert isinstance(runs, list) and len(runs) == 1
