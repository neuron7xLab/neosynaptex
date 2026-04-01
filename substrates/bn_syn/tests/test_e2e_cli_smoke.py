from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_cli_help_end_to_end() -> None:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    completed = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0
    assert "usage" in completed.stdout.lower()
