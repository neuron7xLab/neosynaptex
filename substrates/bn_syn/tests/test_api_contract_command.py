from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_api_contract_command_runs_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.check_api_contract",
            "--baseline",
            "quality/api_contract_baseline.json",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "API contract check passed" in result.stdout
