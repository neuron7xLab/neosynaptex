from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mlsdm.policy.opa import export_opa_policy_data, run_conftest

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "policy"
REGO_DIR = REPO_ROOT / "policies" / "ci"


def test_conftest_passes_on_repo_workflows(tmp_path: Path) -> None:
    if shutil.which("conftest") is None:
        pytest.skip("conftest binary not available")

    data_path = tmp_path / "policy_data.json"
    export_opa_policy_data(POLICY_DIR, data_path)

    workflows = sorted(str(path) for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found to validate"

    result = run_conftest(workflows, data_path, REGO_DIR, REPO_ROOT)
    assert result.returncode == 0, (
        "Conftest failed for repo workflows:\n"
        f"{result.stdout}\n{result.stderr}"
    )
