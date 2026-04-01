from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_workflow_contracts import (
    ContractParseError,
    parse_inventory_table,
    validate_contracts,
)


def write_workflow(path: Path, name: str, on_block: str) -> None:
    path.write_text(
        f"name: {name}\non:\n{on_block}\njobs:\n  verify:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )


def build_contract(total: int, primary: int, reusable: int, rows: list[str]) -> str:
    lines = [
        "# CI/CD Workflow Contracts",
        "",
        f"**Total workflows:** {total}",
        f"**Breakdown:** {primary} primary + {reusable} reusable",
        "",
        "## Workflow Inventory Table (Authoritative)",
        "",
        "| Workflow file | Workflow name | Gate Class | Trigger set | Reusable? |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        "## Next Section",
    ]
    return "\n".join(lines)


def test_missing_row_violation(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(workflows_dir / "alpha.yml", "alpha", "  workflow_dispatch:")
    contracts = build_contract(
        total=1,
        primary=1,
        reusable=0,
        rows=[
            "| `bravo.yml` | `bravo` | long-running | `workflow_dispatch` | NO |",
        ],
    )
    contracts_path = tmp_path / ".github" / "WORKFLOW_CONTRACTS.md"
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(contracts, encoding="utf-8")
    violations = validate_contracts(contracts_path, workflows_dir)
    assert any("MISSING_ROW alpha.yml" in violation for violation in violations)


def test_invalid_gate_class_violation(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(workflows_dir / "alpha.yml", "alpha", "  workflow_dispatch:")
    contracts = build_contract(
        total=1,
        primary=1,
        reusable=0,
        rows=[
            "| `alpha.yml` | `alpha` | invalid-class | `workflow_dispatch` | NO |",
        ],
    )
    contracts_path = tmp_path / ".github" / "WORKFLOW_CONTRACTS.md"
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(contracts, encoding="utf-8")
    violations = validate_contracts(contracts_path, workflows_dir)
    assert any("INVALID_GATE_CLASS alpha.yml" in violation for violation in violations)


def test_pr_gate_requires_pull_request(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(workflows_dir / "alpha.yml", "alpha", "  workflow_dispatch:")
    contracts = build_contract(
        total=1,
        primary=1,
        reusable=0,
        rows=[
            "| `alpha.yml` | `alpha` | PR-gate | `workflow_dispatch` | NO |",
        ],
    )
    contracts_path = tmp_path / ".github" / "WORKFLOW_CONTRACTS.md"
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(contracts, encoding="utf-8")
    violations = validate_contracts(contracts_path, workflows_dir)
    assert any("PR_GATE_NO_PULL_REQUEST alpha.yml" in violation for violation in violations)


def test_counts_mismatch_violation(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    write_workflow(workflows_dir / "alpha.yml", "alpha", "  workflow_dispatch:")
    contracts = build_contract(
        total=2,
        primary=2,
        reusable=0,
        rows=[
            "| `alpha.yml` | `alpha` | long-running | `workflow_dispatch` | NO |",
        ],
    )
    contracts_path = tmp_path / ".github" / "WORKFLOW_CONTRACTS.md"
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(contracts, encoding="utf-8")
    violations = validate_contracts(contracts_path, workflows_dir)
    assert any("COUNT_MISMATCH" in violation for violation in violations)


def test_parse_inventory_table_rejects_duplicate_workflow_rows() -> None:
    text = build_contract(
        total=1,
        primary=1,
        reusable=0,
        rows=[
            "| `alpha.yml` | `alpha` | long-running | `workflow_dispatch` | NO |",
            "| `alpha.yml` | `alpha` | long-running | `workflow_dispatch` | NO |",
        ],
    )

    with pytest.raises(ContractParseError, match="Duplicate workflow rows"):
        parse_inventory_table(text)


def test_validate_contracts_rejects_workflow_without_jobs(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "alpha.yml").write_text(
        "name: alpha\non:\n  workflow_dispatch:\n",
        encoding="utf-8",
    )
    contracts = build_contract(
        total=1,
        primary=1,
        reusable=0,
        rows=["| `alpha.yml` | `alpha` | long-running | `workflow_dispatch` | NO |"],
    )
    contracts_path = tmp_path / ".github" / "WORKFLOW_CONTRACTS.md"
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(contracts, encoding="utf-8")

    with pytest.raises(ContractParseError, match="jobs missing or invalid"):
        validate_contracts(contracts_path, workflows_dir)
