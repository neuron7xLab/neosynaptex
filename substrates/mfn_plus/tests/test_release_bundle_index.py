from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_release_prep_generates_index_and_catalog(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "release_prep.py"
    proc = subprocess.run([sys.executable, str(script)], cwd=root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    release_dir = root / "artifacts" / "release"
    assert (release_dir / "index.html").exists()
    catalog = json.loads((release_dir / "scenario_catalog.json").read_text(encoding="utf-8"))
    assert {"synthetic_morphology", "sensor_grid_anomaly", "regime_transition"} <= set(catalog)
