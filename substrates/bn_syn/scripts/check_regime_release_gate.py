from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _log(event: str, **kwargs: object) -> None:
    payload = {"event": event, **kwargs}
    print(json.dumps(payload, sort_keys=True))


def main() -> int:
    inv = yaml.safe_load((ROOT / "invariants.yaml").read_text(encoding="utf-8"))
    for item in inv["invariants"]:
        if not item.get("test_ref"):
            _log("missing_test_ref", invariant_id=item.get("id"))
            return 1

    required = [
        ROOT / "docs/specs/regime_controller_spec.md",
        ROOT / "docs/features/regime_control_contract.md",
        ROOT / "docs/validation/gamma_proxy_validation.md",
    ]
    for req in required:
        if not req.exists():
            _log("missing_required_file", path=str(req))
            return 1

    prechecks = [
        [sys.executable, "scripts/check_forbidden_claims.py"],
        [sys.executable, "scripts/validate_audit_bundle.py", "docs/audit/final-review-2026"],
    ]
    for pre_cmd in prechecks:
        _log("running_precheck", cmd=pre_cmd)
        pre = subprocess.run(pre_cmd, cwd=str(ROOT), timeout=120, check=False, env=dict(**__import__("os").environ))
        if pre.returncode != 0:
            _log("precheck_failed", cmd=pre_cmd, returncode=pre.returncode)
            return int(pre.returncode)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_regime.py",
        "tests/test_regime_simulation.py",
        "tests/property/test_regime_properties.py",
        "tests/golden/test_regime_golden.py",
        "tests/validation/test_gamma_proxy_synthetic.py",
        "tests/test_invariants_contract.py",
        "tests/test_regime_ledger.py",
        "tests/test_governance_roles.py",
        "tests/test_regime_performance.py",
        "-q",
    ]
    _log("running_pytest", cmd=cmd)
    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str((ROOT / "src").resolve())
    completed = subprocess.run(cmd, cwd=str(ROOT), timeout=600, check=False, env=env)
    _log("pytest_exit", returncode=completed.returncode)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
