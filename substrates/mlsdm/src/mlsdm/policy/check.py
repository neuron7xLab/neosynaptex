from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mlsdm.policy.loader import PolicyLoadError
from mlsdm.policy.opa import (
    PolicyExportError,
    ensure_conftest_available,
    export_opa_policy_data,
    run_conftest,
)
from mlsdm.policy.validation import PolicyValidator

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_policy_dir(policy_dir: Path) -> Path:
    return policy_dir if policy_dir.is_absolute() else (REPO_ROOT / policy_dir).resolve()


def _resolve_output_path(output_path: Path) -> Path:
    return output_path if output_path.is_absolute() else (REPO_ROOT / output_path).resolve()


def _workflow_files(repo_root: Path) -> list[str]:
    workflows_dir = repo_root / ".github" / "workflows"
    return [str(path) for path in sorted(workflows_dir.glob("*.yml"))]


def run_policy_checks(
    *,
    repo_root: Path,
    policy_dir: Path,
    rego_dir: Path,
    data_output: Path,
    stage: str,
) -> int:
    if stage not in {"all", "validate", "export", "workflows", "fixtures"}:
        print(f"ERROR: Unknown stage '{stage}'.")
        return 2

    policy_dir = _resolve_policy_dir(policy_dir)
    data_output = _resolve_output_path(data_output)

    if stage in {"all", "validate"}:
        print("\n=== Stage 1: Validate Policy Contract ===")
        validator = PolicyValidator(repo_root=repo_root, policy_dir=policy_dir)
        if not validator.validate_all():
            return 1
        if stage == "validate":
            return 0

    if stage in {"all", "export"}:
        print("\n=== Stage 2: Export Policy Data ===")
        try:
            export_opa_policy_data(policy_dir, data_output)
        except (PolicyLoadError, PolicyExportError) as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"✓ Exported policy data to {data_output}")
        if stage == "export":
            return 0

    if stage in {"all", "workflows", "fixtures"}:
        try:
            ensure_conftest_available()
        except PolicyExportError as exc:
            print(f"ERROR: {exc}")
            return 1
        if not data_output.exists():
            print(
                "ERROR: Policy data JSON not found. Run "
                f"'python -m mlsdm.policy.check --stage export' to generate {data_output}."
            )
            return 1

    if stage in {"all", "workflows"}:
        print("\n=== Stage 3: Conftest CI Workflow Enforcement ===")
        workflows = _workflow_files(repo_root)
        if not workflows:
            print("ERROR: No workflow files found to validate.")
            return 1
        workflow_result = run_conftest(workflows, data_output, rego_dir, repo_root)
        if workflow_result.returncode != 0:
            print("ERROR: Conftest failed against CI workflows.")
            print(workflow_result.stdout)
            print(workflow_result.stderr)
            return 1
        print("✓ Conftest checks passed for CI workflows.")
        if stage == "workflows":
            return 0

    if stage in {"all", "fixtures"}:
        print("\n=== Stage 4: Conftest Fixture Enforcement ===")
        good_fixtures = [
            "tests/policy/ci/workflow-good.yml",
            "tests/policy/ci/workflow-good-pinned.yml",
            "tests/policy/ci/workflow-good-semver.yml",
        ]
        bad_fixtures = [
            "tests/policy/ci/workflow-bad-permissions.yml",
            "tests/policy/ci/workflow-bad-unpinned.yml",
            "tests/policy/ci/workflow-bad-mutable.yml",
            "tests/policy/ci/workflow-bad-major-version.yml",
        ]
        good_result = run_conftest(good_fixtures, data_output, rego_dir, repo_root)
        if good_result.returncode != 0:
            print("ERROR: Expected good fixtures to pass but conftest failed.")
            print(good_result.stdout)
            print(good_result.stderr)
            return 1

        bad_result = run_conftest(bad_fixtures, data_output, rego_dir, repo_root)
        if bad_result.returncode == 0:
            print("ERROR: Expected bad fixtures to fail but conftest passed.")
            print(bad_result.stdout)
            print(bad_result.stderr)
            return 1

        print("✓ Conftest fixtures behaved as expected.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run policy checks end-to-end")
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=Path("policy"),
        help="Path to policy directory (default: policy/)",
    )
    parser.add_argument(
        "--rego-dir",
        type=Path,
        default=Path("policies/ci"),
        help="Path to rego policy directory (default: policies/ci)",
    )
    parser.add_argument(
        "--data-output",
        type=Path,
        default=Path("build/policy_data.json"),
        help="Path to output policy data JSON (default: build/policy_data.json)",
    )
    parser.add_argument(
        "--stage",
        choices=["all", "validate", "export", "workflows", "fixtures"],
        default="all",
        help="Run a specific stage or all stages (default: all)",
    )
    args = parser.parse_args()

    return run_policy_checks(
        repo_root=REPO_ROOT,
        policy_dir=args.policy_dir,
        rego_dir=_resolve_policy_dir(args.rego_dir),
        data_output=args.data_output,
        stage=args.stage,
    )


if __name__ == "__main__":
    sys.exit(main())
