from __future__ import annotations

from pathlib import Path

from scripts.validate_pr_gates import validate_pr_gates
import pytest
from scripts.validate_pr_gates import PrGateParseError, load_workflow_data


def write_workflow(
    path: Path,
    name: str,
    on_block: str,
    jobs: list[str],
) -> None:
    jobs_block = "\n".join(f"  {job}:\n    runs-on: ubuntu-latest" for job in jobs)
    path.write_text(
        "\n".join(
            [
                f"name: {name}",
                "on:",
                on_block,
                "jobs:",
                jobs_block,
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_pr_gates(path: Path, entries: list[dict[str, object]]) -> None:
    lines = ['version: "1"', "required_pr_gates:"]
    for entry in entries:
        lines.append(f'  - workflow_file: "{entry["workflow_file"]}"')
        lines.append(f'    workflow_name: "{entry["workflow_name"]}"')
        lines.append("    required_job_ids:")
        for job in entry["required_job_ids"]:
            lines.append(f"      - {job}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_contracts(path: Path, rows: list[str]) -> None:
    lines = [
        "# CI/CD Workflow Contracts",
        "",
        "**Total workflows:** 1",
        "**Breakdown:** 1 primary + 0 reusable",
        "",
        "## Workflow Inventory Table (Authoritative)",
        "",
        "| Workflow file | Workflow name | Gate Class | Trigger set | Reusable? |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        "## Next Section",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def test_missing_workflow_file_violation(tmp_path: Path) -> None:
    repo = tmp_path
    workflows_dir = repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    pr_gates_path = repo / ".github" / "PR_GATES.yml"
    pr_gates_path.parent.mkdir(parents=True, exist_ok=True)
    write_pr_gates(
        pr_gates_path,
        [
            {
                "workflow_file": "ci-pr-atomic.yml",
                "workflow_name": "ci-pr-atomic",
                "required_job_ids": ["determinism"],
            }
        ],
    )
    contracts_path = repo / ".github" / "WORKFLOW_CONTRACTS.md"
    write_contracts(
        contracts_path,
        [
            "| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |",
        ],
    )
    violations = validate_pr_gates(pr_gates_path, workflows_dir, contracts_path)
    assert any("MISSING_WORKFLOW_FILE ci-pr-atomic.yml" in v for v in violations)


def test_name_mismatch_violation(tmp_path: Path) -> None:
    repo = tmp_path
    workflows_dir = repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(
        workflows_dir / "ci-pr-atomic.yml",
        name="wrong-name",
        on_block="  pull_request:",
        jobs=["determinism"],
    )
    pr_gates_path = repo / ".github" / "PR_GATES.yml"
    pr_gates_path.parent.mkdir(parents=True, exist_ok=True)
    write_pr_gates(
        pr_gates_path,
        [
            {
                "workflow_file": "ci-pr-atomic.yml",
                "workflow_name": "ci-pr-atomic",
                "required_job_ids": ["determinism"],
            }
        ],
    )
    contracts_path = repo / ".github" / "WORKFLOW_CONTRACTS.md"
    write_contracts(
        contracts_path,
        [
            "| `ci-pr-atomic.yml` | `wrong-name` | PR-gate | `pull_request` | NO |",
        ],
    )
    violations = validate_pr_gates(pr_gates_path, workflows_dir, contracts_path)
    assert any("NAME_MISMATCH ci-pr-atomic.yml" in v for v in violations)


def test_missing_job_id_violation(tmp_path: Path) -> None:
    repo = tmp_path
    workflows_dir = repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(
        workflows_dir / "ci-pr-atomic.yml",
        name="ci-pr-atomic",
        on_block="  pull_request:",
        jobs=["determinism"],
    )
    pr_gates_path = repo / ".github" / "PR_GATES.yml"
    pr_gates_path.parent.mkdir(parents=True, exist_ok=True)
    write_pr_gates(
        pr_gates_path,
        [
            {
                "workflow_file": "ci-pr-atomic.yml",
                "workflow_name": "ci-pr-atomic",
                "required_job_ids": ["quality"],
            }
        ],
    )
    contracts_path = repo / ".github" / "WORKFLOW_CONTRACTS.md"
    write_contracts(
        contracts_path,
        [
            "| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |",
        ],
    )
    violations = validate_pr_gates(pr_gates_path, workflows_dir, contracts_path)
    assert any("MISSING_JOB_IDS ci-pr-atomic.yml" in v for v in violations)


def test_missing_pull_request_violation(tmp_path: Path) -> None:
    repo = tmp_path
    workflows_dir = repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(
        workflows_dir / "ci-pr-atomic.yml",
        name="ci-pr-atomic",
        on_block="  workflow_dispatch:",
        jobs=["determinism"],
    )
    pr_gates_path = repo / ".github" / "PR_GATES.yml"
    pr_gates_path.parent.mkdir(parents=True, exist_ok=True)
    write_pr_gates(
        pr_gates_path,
        [
            {
                "workflow_file": "ci-pr-atomic.yml",
                "workflow_name": "ci-pr-atomic",
                "required_job_ids": ["determinism"],
            }
        ],
    )
    contracts_path = repo / ".github" / "WORKFLOW_CONTRACTS.md"
    write_contracts(
        contracts_path,
        [
            "| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `workflow_dispatch` | NO |",
        ],
    )
    violations = validate_pr_gates(pr_gates_path, workflows_dir, contracts_path)
    assert any("NO_PULL_REQUEST ci-pr-atomic.yml" in v for v in violations)


def test_extra_pr_gate_in_contracts_violation(tmp_path: Path) -> None:
    repo = tmp_path
    workflows_dir = repo / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(
        workflows_dir / "ci-pr-atomic.yml",
        name="ci-pr-atomic",
        on_block="  pull_request:",
        jobs=["determinism"],
    )
    write_workflow(
        workflows_dir / "extra-pr.yml",
        name="extra-pr",
        on_block="  pull_request:",
        jobs=["gate"],
    )
    pr_gates_path = repo / ".github" / "PR_GATES.yml"
    pr_gates_path.parent.mkdir(parents=True, exist_ok=True)
    write_pr_gates(
        pr_gates_path,
        [
            {
                "workflow_file": "ci-pr-atomic.yml",
                "workflow_name": "ci-pr-atomic",
                "required_job_ids": ["determinism"],
            }
        ],
    )
    contracts_path = repo / ".github" / "WORKFLOW_CONTRACTS.md"
    write_contracts(
        contracts_path,
        [
            "| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |",
            "| `extra-pr.yml` | `extra-pr` | PR-gate | `pull_request` | NO |",
        ],
    )
    violations = validate_pr_gates(pr_gates_path, workflows_dir, contracts_path)
    assert any("CONTRACT_PR_GATES_MISMATCH" in v for v in violations)


def test_load_workflow_data_rejects_missing_jobs_mapping(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci-pr-atomic.yml").write_text(
        "name: ci-pr-atomic\non:\n  pull_request:\n",
        encoding="utf-8",
    )

    with pytest.raises(PrGateParseError, match="jobs must be a mapping"):
        load_workflow_data(workflows_dir)
