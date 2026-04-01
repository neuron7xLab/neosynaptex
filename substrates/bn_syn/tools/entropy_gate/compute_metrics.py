from __future__ import annotations

from pathlib import Path
import re
import tomllib
from typing import Any

PIN_OK = re.compile(r"^[A-Za-z0-9_.-]+==[0-9]")
TODO_RE = re.compile(r"\b(TODO|FIXME)\b")
USES_RE = re.compile(r"^\s*-\s*uses:\s*(.+)\s*$")


def _repo_root_from_file(this_file: Path) -> Path:
    path = this_file.resolve()
    for parent in [path.parent, *path.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("NEEDS_EVIDENCE: repo root not found (pyproject.toml missing)")


def _load_pyproject(repo_root: Path) -> dict[str, Any]:
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError("NEEDS_EVIDENCE: pyproject.toml missing")
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))


def _count_unpinned(requirements: list[str]) -> int:
    count = 0
    for requirement in requirements:
        normalized = requirement.strip()
        if not normalized:
            continue
        if PIN_OK.match(normalized):
            continue
        if normalized.startswith("bnsyn[") and normalized.endswith("]"):
            continue
        count += 1
    return count


def _scan_python_offenders(repo_root: Path) -> dict[str, Any]:
    src_root = repo_root / "src"
    offenders_np: list[str] = []
    offenders_py: list[str] = []
    offenders_time: list[str] = []

    if not src_root.exists():
        return {
            "global_np_random_offenders": 0,
            "python_random_offenders": 0,
            "time_calls_offenders": 0,
            "np_offenders": [],
            "py_offenders": [],
            "time_offenders": [],
        }

    for path in sorted(src_root.rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            if "np.random." in stripped:
                if "np.random.Generator" in stripped:
                    continue
                if rel.endswith("/rng.py") or rel == "src/bnsyn/rng.py":
                    continue
                offenders_np.append(f"{rel}:{line_number}:{stripped}")

            if re.search(r"\brandom\.", stripped):
                if rel.endswith("/rng.py") or rel == "src/bnsyn/rng.py":
                    continue
                offenders_py.append(f"{rel}:{line_number}:{stripped}")

            if re.search(r"\b(datetime\.now|datetime\.utcnow|time\.time\(|time\.monotonic\(|time\.perf_counter\()", stripped):
                if rel.startswith("src/bnsyn/tools/"):
                    continue
                if rel == "src/bnsyn/calibration/accuracy_speed.py":
                    continue
                offenders_time.append(f"{rel}:{line_number}:{stripped}")

    return {
        "global_np_random_offenders": len(offenders_np),
        "python_random_offenders": len(offenders_py),
        "time_calls_offenders": len(offenders_time),
        "np_offenders": sorted(offenders_np),
        "py_offenders": sorted(offenders_py),
        "time_offenders": sorted(offenders_time),
    }


def _count_workflow_action_pins(repo_root: Path) -> int:
    workflow_root = repo_root / ".github" / "workflows"
    if not workflow_root.exists():
        return 0

    offenders = 0
    workflow_files = sorted(workflow_root.rglob("*.yml")) + sorted(workflow_root.rglob("*.yaml"))
    for workflow in sorted(set(workflow_files)):
        text = workflow.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            match = USES_RE.match(line)
            if not match:
                continue
            ref = match.group(1).strip()
            if "@" not in ref:
                continue
            _, version = ref.rsplit("@", 1)
            if re.fullmatch(r"[0-9a-fA-F]{40}", version):
                continue
            offenders += 1
    return offenders



def _workflow_hardening_gaps(repo_root: Path) -> dict[str, int]:
    workflow_root = repo_root / ".github" / "workflows"
    if not workflow_root.exists():
        return {
            "gh_workflows_missing_job_permissions_count": 0,
            "gh_workflows_missing_job_timeout_count": 0,
        }

    missing_permissions = 0
    missing_timeout = 0
    workflow_files = sorted(workflow_root.rglob("*.yml")) + sorted(workflow_root.rglob("*.yaml"))
    for workflow in sorted(set(workflow_files)):
        lines = workflow.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_jobs = False
        jobs_indent = 0
        in_job = False
        job_indent = 0
        seen_permissions = False
        seen_timeout = False
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if stripped == "jobs:":
                in_jobs = True
                jobs_indent = indent
                in_job = False
                continue
            if in_jobs and indent <= jobs_indent and not stripped.startswith("-"):
                if in_job:
                    if not seen_permissions:
                        missing_permissions += 1
                    if not seen_timeout:
                        missing_timeout += 1
                in_jobs = False
                in_job = False
            if not in_jobs:
                continue

            if indent == jobs_indent + 2 and stripped.endswith(":") and not stripped.startswith(("permissions:", "timeout-minutes:")):
                if in_job:
                    if not seen_permissions:
                        missing_permissions += 1
                    if not seen_timeout:
                        missing_timeout += 1
                in_job = True
                job_indent = indent
                seen_permissions = False
                seen_timeout = False
                continue

            if in_job and indent <= job_indent:
                if not seen_permissions:
                    missing_permissions += 1
                if not seen_timeout:
                    missing_timeout += 1
                in_job = False

            if in_job and indent >= job_indent + 2:
                if stripped.startswith("permissions:"):
                    seen_permissions = True
                if stripped.startswith("timeout-minutes:"):
                    seen_timeout = True

        if in_job:
            if not seen_permissions:
                missing_permissions += 1
            if not seen_timeout:
                missing_timeout += 1

    return {
        "gh_workflows_missing_job_permissions_count": missing_permissions,
        "gh_workflows_missing_job_timeout_count": missing_timeout,
    }

def _count_todo_fixme(repo_root: Path) -> int:
    src_root = repo_root / "src"
    if not src_root.exists():
        return 0

    count = 0
    for path in sorted(src_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        count += len(TODO_RE.findall(text))
    return count


def compute_metrics(repo_root: Path) -> dict[str, Any]:
    pyproject = _load_pyproject(repo_root)

    project = pyproject.get("project", {})
    dependencies = project.get("dependencies", []) or []
    optional_dependencies = project.get("optional-dependencies", {}) or {}

    build_system = pyproject.get("build-system", {})
    build_requires = build_system.get("requires", []) or []

    lockfiles_present = any(
        (repo_root / name).exists()
        for name in ("requirements-lock.txt", "poetry.lock", "uv.lock", "pdm.lock")
    )
    required_checks_file_present = (repo_root / ".github" / "REQUIRED_CHECKS.yml").exists()

    determinism_metrics = _scan_python_offenders(repo_root)
    workflow_hardening = _workflow_hardening_gaps(repo_root)

    return {
        "version": 1,
        "dependencies": {
            "project_unpinned_count": _count_unpinned(list(dependencies)),
            "optional_unpinned_count": _count_unpinned(
                [item for values in optional_dependencies.values() for item in (values or [])]
            ),
            "build_requires_unpinned_count": _count_unpinned(list(build_requires)),
            "lockfiles_present": bool(lockfiles_present),
        },
        "determinism": {
            "global_np_random_offenders": determinism_metrics["global_np_random_offenders"],
            "python_random_offenders": determinism_metrics["python_random_offenders"],
            "time_calls_offenders": determinism_metrics["time_calls_offenders"],
        },
        "process": {
            "gh_workflows_unpinned_actions_count": _count_workflow_action_pins(repo_root),
            "gh_workflows_missing_job_permissions_count": workflow_hardening["gh_workflows_missing_job_permissions_count"],
            "gh_workflows_missing_job_timeout_count": workflow_hardening["gh_workflows_missing_job_timeout_count"],
            "required_checks_files_present": bool(required_checks_file_present),
        },
        "docs": {
            "src_todo_fixme_count": _count_todo_fixme(repo_root),
        },
        "offenders": {
            "np": determinism_metrics.get("np_offenders", []),
            "py": determinism_metrics.get("py_offenders", []),
            "time": determinism_metrics.get("time_offenders", []),
        },
    }


def flatten(metrics: dict[str, Any], prefix: str = "") -> dict[str, int | bool]:
    flat: dict[str, int | bool] = {}
    for key in sorted(metrics.keys()):
        value = metrics[key]
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten(value, dotted))
        elif isinstance(value, (bool, int)):
            flat[dotted] = value
    return flat
