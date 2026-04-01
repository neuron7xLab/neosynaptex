from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Iterable

from scripts.yaml_contracts import load_yaml_mapping, reject_unknown_keys

ROOT = Path(__file__).resolve().parents[1]


class RequiredStatusContextsParseError(RuntimeError):
    """Raised when REQUIRED_STATUS_CONTEXTS.yml cannot be validated."""


def _load_yaml(path: Path) -> dict[str, object]:
    return load_yaml_mapping(path, RequiredStatusContextsParseError)


def load_required_status_contexts(path: Path) -> list[str]:
    data = _load_yaml(path)
    reject_unknown_keys(
        data,
        {"version", "required_status_contexts"},
        RequiredStatusContextsParseError,
        context=path.name,
    )
    if data.get("version") != "1":
        raise RequiredStatusContextsParseError(f"{path.name} version must be '1'.")
    entries_raw = data.get("required_status_contexts")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise RequiredStatusContextsParseError("required_status_contexts must be a non-empty list.")
    entries: list[str] = []
    for item in entries_raw:
        if not isinstance(item, str) or not item.strip():
            raise RequiredStatusContextsParseError(
                "required_status_contexts entries must be non-empty strings."
            )
        entries.append(item.strip())
    if len(entries) != len(set(entries)):
        raise RequiredStatusContextsParseError("required_status_contexts contains duplicates.")
    return entries


def _normalize_on(data: dict[str, object]) -> object:
    return data.get("on", data.get(True, {}))


def _render_matrix_name(job_name: str, key: str, value: str) -> str:
    pattern = re.compile(r"\$\{\{\s*matrix\." + re.escape(key) + r"\s*\}\}")
    return pattern.sub(value, job_name)


def expected_required_status_contexts(pr_gates_path: Path, workflows_dir: Path) -> list[str]:
    pr_gates = load_yaml_mapping(
        pr_gates_path, RequiredStatusContextsParseError, label="PR_GATES.yml"
    )
    reject_unknown_keys(
        pr_gates,
        {"version", "required_pr_gates"},
        RequiredStatusContextsParseError,
        context="PR_GATES.yml",
    )
    if pr_gates.get("version") != "1":
        raise RequiredStatusContextsParseError("PR_GATES.yml version must be '1'.")
    entries = pr_gates.get("required_pr_gates")
    if not isinstance(entries, list):
        raise RequiredStatusContextsParseError("required_pr_gates must be a list.")

    expected: list[str] = []
    seen_workflows: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RequiredStatusContextsParseError("required_pr_gates entry must be a mapping.")
        workflow_file = entry.get("workflow_file")
        workflow_name = entry.get("workflow_name")
        required_job_ids = entry.get("required_job_ids")
        if not isinstance(workflow_file, str) or not workflow_file:
            raise RequiredStatusContextsParseError("workflow_file/workflow_name must be strings.")
        if not isinstance(workflow_name, str) or not workflow_name.strip():
            raise RequiredStatusContextsParseError("workflow_file/workflow_name must be strings.")
        if workflow_file in seen_workflows:
            raise RequiredStatusContextsParseError(
                f"Duplicate workflow_file in PR_GATES.yml: {workflow_file}"
            )
        seen_workflows.add(workflow_file)
        if not isinstance(required_job_ids, list) or any(
            not isinstance(job, str) or not job for job in required_job_ids
        ):
            raise RequiredStatusContextsParseError(
                "required_job_ids must be a list of non-empty strings."
            )
        normalized_job_ids = [job.strip() for job in required_job_ids]
        if len(set(normalized_job_ids)) != len(normalized_job_ids):
            raise RequiredStatusContextsParseError(
                f"required_job_ids contains duplicates in {workflow_file}."
            )

        wf_path = workflows_dir / workflow_file
        wf = _load_yaml(wf_path)
        jobs = wf.get("jobs")
        if not isinstance(jobs, dict):
            raise RequiredStatusContextsParseError(f"jobs missing in {workflow_file}.")

        for job_id in normalized_job_ids:
            job = jobs.get(job_id)
            if not isinstance(job, dict):
                raise RequiredStatusContextsParseError(
                    f"required job '{job_id}' missing in {workflow_file}."
                )
            job_name = job.get("name")
            if not isinstance(job_name, str) or not job_name.strip():
                job_name = job_id

            strategy = job.get("strategy")
            if isinstance(strategy, dict):
                matrix = strategy.get("matrix")
            else:
                matrix = None

            if (
                isinstance(matrix, dict)
                and "python-version" in matrix
                and isinstance(job_name, str)
            ):
                versions = matrix["python-version"]
                if isinstance(versions, list):
                    for version in versions:
                        if not isinstance(version, str):
                            raise RequiredStatusContextsParseError(
                                f"matrix python-version entries must be strings in {workflow_file}:{job_id}."
                            )
                        rendered = _render_matrix_name(job_name, "python-version", version)
                        expected.append(f"{workflow_name} / {rendered}")
                    continue

            expected.append(f"{workflow_name} / {job_name}")

    return sorted(expected)


def validate_required_status_contexts(
    contexts_path: Path,
    pr_gates_path: Path,
    workflows_dir: Path,
) -> list[str]:
    declared = sorted(load_required_status_contexts(contexts_path))
    expected = expected_required_status_contexts(pr_gates_path, workflows_dir)

    violations: list[str] = []
    declared_set = set(declared)
    expected_set = set(expected)
    if declared_set != expected_set:
        missing = sorted(expected_set - declared_set)
        extra = sorted(declared_set - expected_set)
        violations.append(
            f"VIOLATION: REQUIRED_STATUS_CONTEXTS_MISMATCH expected={expected} declared={declared}"
        )
        if missing:
            violations.append(f"VIOLATION: REQUIRED_STATUS_CONTEXTS_MISSING contexts={missing}")
        if extra:
            violations.append(f"VIOLATION: REQUIRED_STATUS_CONTEXTS_EXTRA contexts={extra}")
    return violations


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 1:
        print("Usage: python -m scripts.validate_required_status_contexts")
        return 3

    contexts_path = ROOT / ".github/REQUIRED_STATUS_CONTEXTS.yml"
    pr_gates_path = ROOT / ".github/PR_GATES.yml"
    workflows_dir = ROOT / ".github/workflows"
    try:
        violations = validate_required_status_contexts(contexts_path, pr_gates_path, workflows_dir)
    except RequiredStatusContextsParseError as exc:
        print(f"VIOLATION: PARSE_ERROR {exc}")
        return 3

    if violations:
        for violation in violations:
            print(violation)
        return 2

    contexts = load_required_status_contexts(contexts_path)
    print(f"OK: required_status_contexts={len(contexts)} validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
