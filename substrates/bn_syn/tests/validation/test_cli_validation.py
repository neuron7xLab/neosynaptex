import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.validation
def test_cli_dtcheck_outputs_metrics() -> None:
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        os.pathsep.join([str(root / "src"), pythonpath]) if pythonpath else str(root / "src")
    )
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "dtcheck",
            "--steps",
            "50",
            "--dt-ms",
            "0.1",
            "--dt2-ms",
            "0.05",
            "--seed",
            "3",
            "--N",
            "50",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    out = json.loads(p.stdout)
    assert "m_dt" in out
    assert "m_dt2" in out
