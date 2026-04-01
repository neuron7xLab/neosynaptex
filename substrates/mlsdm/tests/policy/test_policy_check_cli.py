from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "policy"


def _load_policy(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _write_policy_dir(tmp_path: Path, security_data: dict, observability_data: dict) -> None:
    (tmp_path / "security-baseline.yaml").write_text(
        yaml.safe_dump(security_data, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "observability-slo.yaml").write_text(
        yaml.safe_dump(observability_data, sort_keys=False),
        encoding="utf-8",
    )


def test_policy_check_fails_on_invalid_policy(tmp_path: Path) -> None:
    security = _load_policy(POLICY_DIR / "security-baseline.yaml")
    observability = _load_policy(POLICY_DIR / "observability-slo.yaml")
    security["thresholds"]["coverage_gate_minimum_percent"] = "high"

    _write_policy_dir(tmp_path, security, observability)

    env = dict(os.environ)
    pythonpath = os.pathsep.join(
        [str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
    env["PYTHONPATH"] = pythonpath

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mlsdm.policy.check",
            "--stage",
            "validate",
            "--policy-dir",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0
