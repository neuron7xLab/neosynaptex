from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_quickstart_consistency_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_quickstart_consistency"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "PASSED" in result.stdout


def test_quickstart_consistency_script_fails_when_docs_missing(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_quickstart_consistency"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "file not found" in result.stdout
