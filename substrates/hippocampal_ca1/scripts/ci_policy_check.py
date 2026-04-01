#!/usr/bin/env python3
"""
CI policy checks for GitHub Actions workflows.

Enforces:
  - Top-level permissions must be explicitly set (principle of least privilege)
  - All actions must be pinned to immutable SHAs (no floating tags)
  - pull_request_target trigger is blocked by default
  - chmod/chown on runner work/temp directories is disallowed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - surfaced in CI
    print(f"PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(1)


WORKFLOW_DIR = Path(".github/workflows")
SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
RUNNER_PATH_PATTERN = re.compile(
    r"(/__w/)|(\${{\s*runner\.temp\s*}})|(\$RUNNER_TEMP)|(\${RUNNER_TEMP})",
    re.IGNORECASE,
)
CHMOD_PATTERN = re.compile(r"\b(?:sudo\s+)?(?:chmod|chown)\b", re.IGNORECASE)


def load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        print(f"{path}:1:1 YAML parse error: {exc}")
        return None
    except OSError as exc:
        print(f"{path}:1:1 Cannot read file: {exc}")
        return None


def find_line_number(lines: list[str], needle: str) -> int:
    for idx, line in enumerate(lines, start=1):
        if needle in line:
            return idx
    return 1


def find_trigger_line(lines: list[str], trigger: str) -> int:
    pattern = re.compile(rf"^\s*-?\s*{re.escape(trigger)}\b", re.IGNORECASE)
    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if pattern.search(stripped):
            return idx
    return 1


def is_pinned(uses_value: str) -> bool:
    if uses_value.startswith("./"):
        # Local composite actions are trusted to be reviewed as part of the repo
        return True
    if uses_value.startswith("docker://"):
        return "@sha256:" in uses_value
    if "@" not in uses_value:
        return False
    ref = uses_value.split("@", 1)[1]
    return bool(SHA_PATTERN.fullmatch(ref))


def extract_triggers(on_field: Any) -> set[str]:
    triggers: set[str] = set()
    if isinstance(on_field, str):
        triggers.add(on_field)
    elif isinstance(on_field, list):
        for item in on_field:
            if isinstance(item, str):
                triggers.add(item)
    elif isinstance(on_field, dict):
        triggers.update(on_field.keys())
    return triggers


def check_workflow(path: Path) -> list[str]:
    issues: list[str] = []
    content = path.read_text(encoding="utf-8").splitlines()
    data = load_yaml(path)
    if data is None:
        return issues if issues else [f"{path}:1:1 Failed to parse workflow"]

    # Enforce explicit permissions
    if not isinstance(data, dict) or "permissions" not in data:
        issues.append(f"{path}:1:1 Missing top-level permissions block")

    # Block pull_request_target usage
    triggers = extract_triggers(data.get("on", {})) if isinstance(data, dict) else set()
    if "pull_request_target" in triggers:
        line_no = find_trigger_line(content, "pull_request_target")
        issues.append(f"{path}:{line_no}: pull_request_target trigger is disallowed")

    # Validate jobs/steps for pinned actions and chmod/chown
    jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
    if isinstance(jobs, dict):
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                uses_value = step.get("uses")
                if isinstance(uses_value, str) and not is_pinned(uses_value):
                    line_no = find_line_number(content, uses_value)
                    issues.append(f"{path}:{line_no}: action '{uses_value}' is not pinned to a SHA")

                run_value = step.get("run")
                if isinstance(run_value, str):
                    for line in run_value.splitlines():
                        if CHMOD_PATTERN.search(line) and RUNNER_PATH_PATTERN.search(line):
                            line_no = find_line_number(content, line.strip())
                            issues.append(
                                f"{path}:{line_no}: disallowed chmod/chown on runner workspace/temp"
                            )

    return issues


def main() -> int:
    if not WORKFLOW_DIR.is_dir():
        print("No .github/workflows directory found", file=sys.stderr)
        return 1

    workflow_files = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))

    violations: list[str] = []
    for wf in workflow_files:
        violations.extend(check_workflow(wf))

    if violations:
        print("CI policy violations detected:")
        for violation in violations:
            print(violation)
        return 1

    print("All workflows comply with CI policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
