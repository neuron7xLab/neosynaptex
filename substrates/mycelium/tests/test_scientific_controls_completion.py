from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_neurochem_controls_cover_required_scientific_checks() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(root / "validation" / "neurochem_controls.py")],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(
        (
            root
            / "artifacts"
            / "evidence"
            / "neurochem_controls"
            / "neurochem_controls_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["status"] == "PASS"
    assert payload["controls"]["observation_noise_control"] is True
    assert payload["controls"]["high_inhibition_recovery"] is True
    assert payload["controls"]["occupancy_bounds"] is True
    assert payload["controls"]["desensitization_recovery"] is True
    assert payload["controls"]["baseline_compatibility"] is True
