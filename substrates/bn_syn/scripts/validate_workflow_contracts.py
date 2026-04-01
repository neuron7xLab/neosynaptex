from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable

from scripts.yaml_contracts import load_yaml_mapping

ALLOWED_GATE_CLASSES = {"PR-gate", "long-running"}
ALLOWED_REUSABLE_VALUES = {"YES", "NO"}
TRIGGER_ORDER = (
    "pull_request",
    "push",
    "schedule",
    "workflow_dispatch",
    "workflow_call",
)


class ContractParseError(RuntimeError):
    """Raised when workflow contracts cannot be parsed deterministically."""


@dataclass(frozen=True)
class InventoryRow:
    workflow_file: str
    workflow_name: str
    gate_class: str
    triggers: tuple[str, ...]
    reusable: bool
    has_exception: bool


def normalize_on_section(on_section: object) -> tuple[str, ...]:
    triggers: set[str] = set()
    if isinstance(on_section, str):
        triggers.add(on_section)
    elif isinstance(on_section, list):
        triggers.update(str(item) for item in on_section)
    elif isinstance(on_section, dict):
        triggers.update(str(key) for key in on_section.keys())
    ordered = [name for name in TRIGGER_ORDER if name in triggers]
    unknown = sorted(trigger for trigger in triggers if trigger not in TRIGGER_ORDER)
    ordered.extend(unknown)
    return tuple(ordered)


def parse_counts(text: str) -> tuple[int, int, int]:
    total_match = re.search(r"^\*\*Total workflows:\*\*\s*(\d+)\s*$", text, re.M)
    breakdown_match = re.search(
        r"^\*\*Breakdown:\*\*\s*(\d+)\s+primary\s+\+\s+(\d+)\s+reusable\s*$",
        text,
        re.M,
    )
    if not total_match or not breakdown_match:
        raise ContractParseError("Missing total/breakdown counts in contracts.")
    total = int(total_match.group(1))
    primary = int(breakdown_match.group(1))
    reusable = int(breakdown_match.group(2))
    return total, primary, reusable


def parse_inventory_table(text: str) -> dict[str, InventoryRow]:
    lines = text.splitlines()
    header = "| Workflow file | Workflow name | Gate Class | Trigger set | Reusable? |"
    try:
        header_index = next(i for i, line in enumerate(lines) if line.strip() == header)
    except StopIteration as exc:
        raise ContractParseError("Workflow Inventory Table header not found.") from exc

    rows: dict[str, InventoryRow] = {}
    duplicate_rows: set[str] = set()
    last_row: str | None = None
    for line in lines[header_index + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped or stripped == "---":
            continue
        if stripped.startswith("EXCEPTION:") or stripped.startswith("> EXCEPTION:"):
            if not last_row:
                raise ContractParseError("EXCEPTION line without preceding workflow row.")
            row = rows[last_row]
            rows[last_row] = InventoryRow(
                workflow_file=row.workflow_file,
                workflow_name=row.workflow_name,
                gate_class=row.gate_class,
                triggers=row.triggers,
                reusable=row.reusable,
                has_exception=True,
            )
            continue
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 5:
            raise ContractParseError(f"Invalid inventory table row: {line}")
        if cells[0].startswith("---"):
            continue
        workflow_file = cells[0].strip("` ")
        workflow_name = cells[1].strip("` ")
        gate_class = cells[2].strip()
        triggers_raw = cells[3].strip("` ")
        reusable_raw = cells[4].strip()
        if reusable_raw not in ALLOWED_REUSABLE_VALUES:
            raise ContractParseError(
                f"Invalid reusable value '{reusable_raw}' for {workflow_file}."
            )
        triggers = tuple(trigger.strip() for trigger in triggers_raw.split(",") if trigger.strip())
        if workflow_file in rows:
            duplicate_rows.add(workflow_file)
        rows[workflow_file] = InventoryRow(
            workflow_file=workflow_file,
            workflow_name=workflow_name,
            gate_class=gate_class,
            triggers=triggers,
            reusable=reusable_raw == "YES",
            has_exception=False,
        )
        last_row = workflow_file
    if not rows:
        raise ContractParseError("Workflow Inventory Table has no rows.")
    if duplicate_rows:
        raise ContractParseError(f"Duplicate workflow rows: {sorted(duplicate_rows)}")
    return rows


def load_workflow_inventory(workflows_dir: Path) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for workflow_path in sorted(workflows_dir.glob("*.yml")):
        data = load_yaml_mapping(
            workflow_path,
            ContractParseError,
            label=f"workflow file {workflow_path.name}",
        )
        on_section = data.get("on", data.get(True, {}))
        triggers = normalize_on_section(on_section)
        jobs_raw = data.get("jobs")
        if not isinstance(jobs_raw, dict):
            raise ContractParseError(f"jobs missing or invalid in workflow: {workflow_path.name}")
        name = data.get("name", "UNKNOWN")
        reusable = "workflow_call" in triggers or workflow_path.name.startswith("_reusable_")
        inventory[workflow_path.name] = {
            "name": str(name) if name is not None else "UNKNOWN",
            "triggers": triggers,
            "reusable": reusable,
            "prefix_reusable": workflow_path.name.startswith("_reusable_"),
        }
    return inventory


def validate_contracts(contracts_path: Path, workflows_dir: Path) -> list[str]:
    text = contracts_path.read_text(encoding="utf-8")
    total, primary, reusable = parse_counts(text)
    rows = parse_inventory_table(text)
    actual = load_workflow_inventory(workflows_dir)

    violations: list[str] = []

    expected_files = set(rows.keys())
    actual_files = set(actual.keys())
    missing_rows = sorted(actual_files - expected_files)
    for workflow in missing_rows:
        violations.append(f"VIOLATION: MISSING_ROW {workflow}")
    extra_rows = sorted(expected_files - actual_files)
    for workflow in extra_rows:
        violations.append(f"VIOLATION: EXTRA_ROW {workflow}")

    actual_total = len(actual_files)
    actual_reusable = sum(1 for data in actual.values() if data["reusable"])
    actual_primary = actual_total - actual_reusable
    if (total, primary, reusable) != (actual_total, actual_primary, actual_reusable):
        violations.append(
            "VIOLATION: COUNT_MISMATCH "
            f"contracts=({total},{primary},{reusable}) "
            f"actual=({actual_total},{actual_primary},{actual_reusable})"
        )

    for workflow_file in sorted(expected_files & actual_files):
        row = rows[workflow_file]
        actual_row = actual[workflow_file]
        if row.gate_class not in ALLOWED_GATE_CLASSES:
            violations.append(f"VIOLATION: INVALID_GATE_CLASS {workflow_file} {row.gate_class}")
        if row.workflow_name != actual_row["name"]:
            violations.append(
                "VIOLATION: NAME_MISMATCH "
                f"{workflow_file} expected={row.workflow_name} "
                f"actual={actual_row['name']}"
            )
        if tuple(row.triggers) != tuple(actual_row["triggers"]):
            violations.append(
                "VIOLATION: TRIGGER_MISMATCH "
                f"{workflow_file} expected={row.triggers} "
                f"actual={actual_row['triggers']}"
            )
        if row.reusable != bool(actual_row["reusable"]):
            violations.append(
                "VIOLATION: REUSABLE_MISMATCH "
                f"{workflow_file} expected={row.reusable} "
                f"actual={actual_row['reusable']}"
            )
        if actual_row["prefix_reusable"] and "workflow_call" not in actual_row["triggers"]:
            violations.append(
                f"VIOLATION: AMBIGUOUS_REUSABLE {workflow_file} missing workflow_call trigger"
            )
        if row.gate_class == "PR-gate":
            if "pull_request" not in actual_row["triggers"] and not row.has_exception:
                violations.append(
                    f"VIOLATION: PR_GATE_NO_PULL_REQUEST {workflow_file} requires EXCEPTION entry"
                )

    return sorted(violations)


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 1:
        print("Usage: python -m scripts.validate_workflow_contracts")
        return 3
    contracts_path = Path(".github/WORKFLOW_CONTRACTS.md")
    workflows_dir = Path(".github/workflows")
    try:
        violations = validate_contracts(contracts_path, workflows_dir)
    except ContractParseError as exc:
        print(f"PARSE_ERROR: {exc}")
        return 3
    if violations:
        for violation in violations:
            print(violation)
        return 2
    print("Workflow contracts validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
