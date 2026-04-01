from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from mlsdm.policy.loader import load_policy_bundle
from mlsdm.policy.registry import build_policy_registry, write_policy_registry


def _copy_policy_files(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in ("security-baseline.yaml", "observability-slo.yaml"):
        (target_dir / name).write_text((source_dir / name).read_text(encoding="utf-8"), encoding="utf-8")


def test_policy_registry_cli_fails_on_drift(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policy"
    _copy_policy_files(Path("policy"), policy_dir)

    bundle = load_policy_bundle(policy_dir, enforce_registry=False)
    registry = build_policy_registry(
        policy_hash="deadbeef" * 8,
        policy_contract_version=bundle.security_baseline.policy_contract_version,
    )
    write_policy_registry(policy_dir / "registry.json", registry)

    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_root}:{env.get('PYTHONPATH', '')}".rstrip(":")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mlsdm.policy.registry_check",
            "--policy-dir",
            str(policy_dir),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Policy registry verification failed" in result.stdout + result.stderr
