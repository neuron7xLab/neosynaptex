from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Iterable

import yaml


class GovernanceParseError(RuntimeError):
    """Raised when governance files cannot be parsed into policy inputs."""



def _load_required_status_contexts(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GovernanceParseError("REQUIRED_STATUS_CONTEXTS.yml must be a mapping.")
    contexts = data.get("required_status_contexts")
    if not isinstance(contexts, list) or any(not isinstance(c, str) for c in contexts):
        raise GovernanceParseError("required_status_contexts must be a list of strings.")
    return contexts


def validate_governance_doc(doc_path: Path, contexts_path: Path) -> list[str]:
    text = doc_path.read_text(encoding="utf-8")
    required_sections = (
        "# Branch Protection Governance Baseline (`main`)",
        "## Mandatory repository settings",
        "## Required status contexts (job-level + matrix-level)",
        "## Governance-proof evidence (blocking semantics)",
        "## Control PR protocol (negative testing)",
        "### Control PR evidence log",
    )
    violations: list[str] = []
    for section in required_sections:
        if section not in text:
            violations.append(f"VIOLATION: MISSING_SECTION {section}")

    contexts = _load_required_status_contexts(contexts_path)
    for context in contexts:
        needle = f"- `{context}`"
        if needle not in text:
            violations.append(f"VIOLATION: MISSING_REQUIRED_CONTEXT {context}")

    required_controls = (
        "Control PR #1",
        "Control PR #2",
        "Control PR #3",
        "Control PR #4",
        "Control PR #5",
    )
    for control in required_controls:
        if control not in text:
            violations.append(f"VIOLATION: MISSING_CONTROL_PROTOCOL {control}")

    checklist_matches = re.findall(r"^\d+\. \[ \] ", text, flags=re.MULTILINE)
    if len(checklist_matches) < 10:
        violations.append("VIOLATION: INCOMPLETE_MANDATORY_SETTINGS_CHECKLIST")

    return violations


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 1:
        print("Usage: python -m scripts.validate_branch_protection_governance")
        return 3

    doc_path = Path(".github/BRANCH_PROTECTION_GOVERNANCE.md")
    contexts_path = Path(".github/REQUIRED_STATUS_CONTEXTS.yml")

    try:
        violations = validate_governance_doc(doc_path, contexts_path)
    except GovernanceParseError as exc:
        print(f"VIOLATION: PARSE_ERROR {exc}")
        return 3

    if violations:
        for violation in violations:
            print(violation)
        return 2

    print("OK: branch protection governance document validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
