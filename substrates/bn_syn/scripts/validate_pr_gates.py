from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

from scripts.yaml_contracts import load_yaml_mapping, reject_unknown_keys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_workflow_contracts import ContractParseError, parse_inventory_table  # noqa: E402


class PrGateParseError(RuntimeError):
    """Raised when PR gate workflow contracts fail parsing or validation."""


@dataclass(frozen=True)
class PrGateEntry:
    workflow_file: str
    workflow_name: str
    required_job_ids: tuple[str, ...]


def load_pr_gates(pr_gates_path: Path) -> list[PrGateEntry]:
    data = load_yaml_mapping(pr_gates_path, PrGateParseError, label="PR_GATES.yml")
    reject_unknown_keys(
        data,
        {"version", "required_pr_gates"},
        PrGateParseError,
        context="PR_GATES.yml",
    )
    version = data.get("version")
    if version != "1":
        raise PrGateParseError("PR_GATES.yml version must be '1'.")
    entries_raw = data.get("required_pr_gates")
    if not isinstance(entries_raw, list):
        raise PrGateParseError("required_pr_gates must be a list.")
    entries: list[PrGateEntry] = []
    seen_files: set[str] = set()
    for entry in entries_raw:
        if not isinstance(entry, dict):
            raise PrGateParseError("Each required_pr_gates entry must be a mapping.")
        entry_keys = set(entry.keys())
        expected_keys = {"workflow_file", "workflow_name", "required_job_ids"}
        if entry_keys != expected_keys:
            raise PrGateParseError(
                "Each required_pr_gates entry must contain exactly "
                "workflow_file, workflow_name, required_job_ids."
            )
        workflow_file = entry["workflow_file"]
        workflow_name = entry["workflow_name"]
        required_job_ids = entry["required_job_ids"]
        if not isinstance(workflow_file, str) or not workflow_file:
            raise PrGateParseError("workflow_file must be a non-empty string.")
        if not isinstance(workflow_name, str) or not workflow_name:
            raise PrGateParseError("workflow_name must be a non-empty string.")
        if not isinstance(required_job_ids, list) or not required_job_ids:
            raise PrGateParseError("required_job_ids must be a non-empty list.")
        if any(not isinstance(job, str) or not job for job in required_job_ids):
            raise PrGateParseError("required_job_ids must be non-empty strings.")
        if workflow_file in seen_files:
            raise PrGateParseError(f"Duplicate workflow_file: {workflow_file}")
        seen_files.add(workflow_file)
        entries.append(
            PrGateEntry(
                workflow_file=workflow_file,
                workflow_name=workflow_name,
                required_job_ids=tuple(required_job_ids),
            )
        )
    if not entries:
        raise PrGateParseError("required_pr_gates must not be empty.")
    return entries


def has_pull_request(on_section: object) -> bool:
    if isinstance(on_section, str):
        return on_section == "pull_request"
    if isinstance(on_section, list):
        return "pull_request" in on_section
    if isinstance(on_section, dict):
        return "pull_request" in on_section
    return False


def load_workflow_data(workflows_dir: Path) -> dict[str, dict[str, object]]:
    workflow_data: dict[str, dict[str, object]] = {}
    for workflow_path in sorted(workflows_dir.glob("*.yml")):
        data = load_yaml_mapping(
            workflow_path,
            PrGateParseError,
            label=f"workflow file {workflow_path.name}",
        )
        on_section = data.get("on", data.get(True, {}))
        jobs_raw = data.get("jobs")
        if not isinstance(jobs_raw, dict):
            raise PrGateParseError(f"jobs must be a mapping in workflow: {workflow_path.name}")
        workflow_data[workflow_path.name] = {
            "name": str(data.get("name", workflow_path.stem)),
            "jobs": sorted(jobs_raw.keys()),
            "has_pr": has_pull_request(on_section),
        }
    return workflow_data


def load_contract_pr_gates(contracts_path: Path) -> set[str]:
    text = contracts_path.read_text(encoding="utf-8")
    rows = parse_inventory_table(text)
    return {workflow for workflow, row in rows.items() if row.gate_class == "PR-gate"}


def validate_pr_gates(
    pr_gates_path: Path,
    workflows_dir: Path,
    contracts_path: Path,
) -> list[str]:
    entries = load_pr_gates(pr_gates_path)
    workflow_data = load_workflow_data(workflows_dir)
    contract_pr_gates = load_contract_pr_gates(contracts_path)

    violations: list[str] = []
    expected_files = {entry.workflow_file for entry in entries}

    for entry in entries:
        if entry.workflow_file not in workflow_data:
            violations.append(f"VIOLATION: MISSING_WORKFLOW_FILE {entry.workflow_file}")
            continue
        data = workflow_data[entry.workflow_file]
        if entry.workflow_name != data["name"]:
            violations.append(
                "VIOLATION: NAME_MISMATCH "
                f"{entry.workflow_file} expected={entry.workflow_name} "
                f"actual={data['name']}"
            )
        if not data["has_pr"]:
            violations.append(f"VIOLATION: NO_PULL_REQUEST {entry.workflow_file}")
        required_jobs = set(entry.required_job_ids)
        actual_jobs = set(data["jobs"])
        missing_jobs = sorted(required_jobs - actual_jobs)
        if missing_jobs:
            violations.append(
                f"VIOLATION: MISSING_JOB_IDS {entry.workflow_file} missing={missing_jobs}"
            )

    pr_triggered = {workflow for workflow, data in workflow_data.items() if data["has_pr"]}
    if contract_pr_gates != expected_files:
        violations.append(
            "VIOLATION: CONTRACT_PR_GATES_MISMATCH "
            f"contracts={sorted(contract_pr_gates)} "
            f"ssot={sorted(expected_files)}"
        )
    missing_pr_gate_triggers = sorted(contract_pr_gates - pr_triggered)
    if missing_pr_gate_triggers:
        violations.append(
            f"VIOLATION: CONTRACT_PR_GATE_NO_PULL_REQUEST workflows={missing_pr_gate_triggers}"
        )

    for workflow_file in sorted(workflow_data):
        if not workflow_file.startswith("ci-pr"):
            continue
        if workflow_file == "ci-pr-atomic.yml":
            continue
        if workflow_file in expected_files:
            violations.append(f"VIOLATION: CI_PR_WRAPPER_IN_SSOT {workflow_file}")
        if workflow_file in contract_pr_gates:
            violations.append(f"VIOLATION: CI_PR_WRAPPER_IN_CONTRACTS {workflow_file}")

    return sorted(violations)


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 1:
        print("Usage: python -m scripts.validate_pr_gates")
        return 3
    pr_gates_path = Path(".github/PR_GATES.yml")
    workflows_dir = Path(".github/workflows")
    contracts_path = Path(".github/WORKFLOW_CONTRACTS.md")
    try:
        violations = validate_pr_gates(pr_gates_path, workflows_dir, contracts_path)
    except (PrGateParseError, ContractParseError) as exc:
        print(f"VIOLATION: PARSE_ERROR {exc}")
        return 3
    if violations:
        for violation in violations:
            print(violation)
        return 2
    print(
        f"OK: pr_gates={len(load_pr_gates(pr_gates_path))} workflows={len(list(workflows_dir.glob('*.yml')))} validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
