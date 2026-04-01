from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_library_integration_example_runs() -> None:
    result = subprocess.run(
        [sys.executable, "examples/integration/library_minimal.py"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    payload = json.loads(result.stdout)
    assert payload["example"] == "library_minimal"
    assert payload["seed"] == 123
    assert "sigma_mean" in payload["metrics"]


def test_cli_integration_example_runs(tmp_path: Path) -> None:
    out_file = tmp_path / "cli_result.json"
    subprocess.run(
        ["examples/integration/cli_minimal.sh", str(out_file)],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "demo" in payload
    assert set(payload["demo"]) == {"sigma_mean", "sigma_std", "rate_mean_hz", "rate_std"}
