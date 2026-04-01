from __future__ import annotations

from pathlib import Path
import sys
from typing import Iterable

from scripts.yaml_contracts import load_yaml_mapping, reject_unknown_keys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_workflow_contracts import ContractParseError, parse_inventory_table  # noqa: E402


class RequiredChecksParseError(RuntimeError):
    """Raised when REQUIRED_CHECKS.yml violates the governance schema."""


def load_required_checks(required_checks_path: Path) -> list[str]:
    data = load_yaml_mapping(
        required_checks_path,
        RequiredChecksParseError,
        label="REQUIRED_CHECKS.yml",
    )
    reject_unknown_keys(
        data,
        {"version", "required_checks"},
        RequiredChecksParseError,
        context="REQUIRED_CHECKS.yml",
    )
    version = data.get("version")
    if version != "1":
        raise RequiredChecksParseError("REQUIRED_CHECKS.yml version must be '1'.")
    entries_raw = data.get("required_checks")
    if not isinstance(entries_raw, list):
        raise RequiredChecksParseError("required_checks must be a list.")
    entries: list[str] = []
    seen_workflows: set[str] = set()
    for entry in entries_raw:
        if not isinstance(entry, dict):
            raise RequiredChecksParseError("Each required_checks entry must be a mapping.")
        entry_keys = set(entry.keys())
        if entry_keys != {"workflow_file"}:
            raise RequiredChecksParseError(
                "Each required_checks entry must contain exactly workflow_file."
            )
        workflow_file = entry["workflow_file"]
        if not isinstance(workflow_file, str) or not workflow_file:
            raise RequiredChecksParseError("workflow_file must be a non-empty string.")
        if workflow_file in seen_workflows:
            raise RequiredChecksParseError(f"Duplicate workflow_file: {workflow_file}")
        seen_workflows.add(workflow_file)
        entries.append(workflow_file)
    if not entries:
        raise RequiredChecksParseError("required_checks must not be empty.")
    return entries


def load_contract_pr_gates(contracts_path: Path) -> set[str]:
    text = contracts_path.read_text(encoding="utf-8")
    rows = parse_inventory_table(text)
    return {workflow for workflow, row in rows.items() if row.gate_class == "PR-gate"}


def validate_required_checks(
    required_checks_path: Path,
    contracts_path: Path,
) -> list[str]:
    required_checks = load_required_checks(required_checks_path)
    contract_pr_gates = load_contract_pr_gates(contracts_path)
    required_set = set(required_checks)
    violations: list[str] = []
    if required_set != contract_pr_gates:
        missing = sorted(contract_pr_gates - required_set)
        extra = sorted(required_set - contract_pr_gates)
        message = (
            "VIOLATION: REQUIRED_CHECKS_MISMATCH "
            f"contracts={sorted(contract_pr_gates)} "
            f"required_checks={sorted(required_set)}"
        )
        violations.append(message)
        if missing:
            violations.append(f"VIOLATION: REQUIRED_CHECKS_MISSING workflows={missing}")
        if extra:
            violations.append(f"VIOLATION: REQUIRED_CHECKS_EXTRA workflows={extra}")
    return sorted(violations)


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) == 2 and args[1] in {"-h", "--help"}:
        print("Usage: python -m scripts.validate_required_checks")
        return 0
    if len(args) != 1:
        print("Usage: python -m scripts.validate_required_checks")
        return 3
    required_checks_path = Path(".github/REQUIRED_CHECKS.yml")
    contracts_path = Path(".github/WORKFLOW_CONTRACTS.md")
    try:
        violations = validate_required_checks(required_checks_path, contracts_path)
    except (RequiredChecksParseError, ContractParseError) as exc:
        print(f"VIOLATION: PARSE_ERROR {exc}")
        return 3
    if violations:
        for violation in violations:
            print(violation)
        return 2
    print(
        "OK: required_checks="
        f"{len(load_required_checks(required_checks_path))} "
        f"contract_pr_gates={len(load_contract_pr_gates(contracts_path))} validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
