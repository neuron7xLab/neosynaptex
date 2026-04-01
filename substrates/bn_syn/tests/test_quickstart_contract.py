from __future__ import annotations

import json
import os
import subprocess
import sys


def test_quickstart_contract_demo_command() -> None:
    cmd = [
        sys.executable,
        "-m",
        "bnsyn.cli",
        "demo",
        "--steps",
        "120",
        "--dt-ms",
        "0.1",
        "--seed",
        "123",
        "--N",
        "32",
    ]
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    payload = json.loads(result.stdout)
    demo = payload["demo"]
    assert set(demo) == {"sigma_mean", "sigma_std", "rate_mean_hz", "rate_std"}
    assert 0.0 <= float(demo["sigma_mean"]) <= 5.0
    assert 0.0 <= float(demo["rate_mean_hz"]) <= 1000.0
