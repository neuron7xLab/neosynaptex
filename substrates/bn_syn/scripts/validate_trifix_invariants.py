from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CANONICAL_WORKFLOW = WORKFLOWS_DIR / "ci-pr-atomic.yml"
MAKEFILE = REPO_ROOT / "Makefile"
PRECOMMIT = REPO_ROOT / ".pre-commit-config.yaml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
TESTING_DOC = REPO_ROOT / "docs" / "TESTING.md"

TEST_INSTALL_CMD = 'python -m pip install -e ".[test]"'
CANONICAL_GATE_CMD = "make test-gate"
CANONICAL_TEST_CMD = "$(PYTHON) -m pytest -m \"not (validation or property)\" -q"
COLLECT_CMD = "python -m pytest --collect-only -q"
VALIDATOR_CMD = "python -m scripts.validate_trifix_invariants"
COMMAND_TIMEOUT_SECONDS = 1800


class ValidationError(RuntimeError):
    pass


def _read(path: Path) -> str:
    if not path.exists():
        raise ValidationError(f"required file not found: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def _check_top_level_permissions() -> None:
    missing: list[str] = []
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        lines = workflow.read_text(encoding="utf-8").splitlines()
        if not any(line.startswith("permissions:") for line in lines):
            missing.append(str(workflow.relative_to(REPO_ROOT)))
    if missing:
        raise ValidationError(
            "I1 violation: workflows missing top-level permissions: " + ", ".join(missing)
        )


def _extract_tool_versions() -> dict[str, set[str]]:
    versions: dict[str, set[str]] = {"ruff": set(), "bandit": set()}

    pyproject = _read(PYPROJECT)
    for tool in ("ruff", "bandit"):
        for match in re.findall(rf'"{tool}==([^"]+)"', pyproject):
            versions[tool].add(match)

    precommit = _read(PRECOMMIT)
    tool_repo = None
    for line in precommit.splitlines():
        repo_match = re.search(r"repo:\s*(.+)$", line)
        if repo_match:
            repo_val = repo_match.group(1)
            if "ruff-pre-commit" in repo_val:
                tool_repo = "ruff"
            elif "PyCQA/bandit" in repo_val:
                tool_repo = "bandit"
            else:
                tool_repo = None
            continue

        rev_match = re.search(r"^\s*rev:\s*v?([0-9][^\s]*)", line)
        if rev_match and tool_repo:
            versions[tool_repo].add(rev_match.group(1))
            tool_repo = None

        if "additional_dependencies:" in line:
            for tool in ("ruff", "bandit"):
                for match in re.findall(rf"{tool}==([^\],\s]+)", line):
                    versions[tool].add(match)

    return versions


def _check_tool_versions() -> None:
    versions = _extract_tool_versions()
    for tool, vals in versions.items():
        if not vals:
            raise ValidationError(f"I2 violation: no pinned {tool} version found")
        if len(vals) != 1:
            raise ValidationError(
                f"I2 violation: multiple {tool} versions detected: {sorted(vals)}"
            )


def _check_canonical_workflow() -> None:
    wf_text = _read(CANONICAL_WORKFLOW)
    if TEST_INSTALL_CMD not in wf_text:
        raise ValidationError("I3 violation: canonical workflow missing TEST_INSTALL_CMD")
    if COLLECT_CMD not in wf_text:
        raise ValidationError("I3 violation: canonical workflow missing collect-only step")
    if VALIDATOR_CMD not in wf_text:
        raise ValidationError("I3 violation: canonical workflow missing validator step")
    if CANONICAL_GATE_CMD not in wf_text:
        raise ValidationError("I3 violation: canonical workflow missing canonical gate command")

    install_pos = wf_text.find(TEST_INSTALL_CMD)
    collect_pos = wf_text.find(COLLECT_CMD)
    validator_pos = wf_text.find(VALIDATOR_CMD)
    gate_pos = wf_text.find(CANONICAL_GATE_CMD)
    if not (install_pos < collect_pos < validator_pos < gate_pos):
        raise ValidationError(
            "I3 violation: install -> collect -> validator -> gate ordering is not enforced"
        )


def _check_ssot_strings() -> None:
    makefile = _read(MAKEFILE)
    if f"TEST_CMD ?= {CANONICAL_TEST_CMD}" not in makefile:
        raise ValidationError("I3 violation: Makefile TEST_CMD is out of SSOT sync")
    if "test-gate:\n\t$(TEST_CMD)" not in makefile:
        raise ValidationError("I3 violation: Makefile test-gate target is out of SSOT sync")

    for doc in (README, TESTING_DOC):
        if not doc.exists():
            continue
        text = _read(doc)
        if "make test-gate" in text and CANONICAL_GATE_CMD not in text:
            raise ValidationError(
                f"I3 violation: {doc.relative_to(REPO_ROOT)} gate command does not match canonical"
            )
        if ".[test]" in text and TEST_INSTALL_CMD not in text:
            raise ValidationError(
                f"I3 violation: {doc.relative_to(REPO_ROOT)} install command does not match canonical"
            )


def _run(cmd: str) -> str:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        shell=True,
        text=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
        check=False,
    )
    out = f"{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        raise ValidationError(f"command failed ({cmd}) with exit {proc.returncode}\n{out}")
    return out


def _deps_missing() -> bool:
    required_modules = ("yaml", "hypothesis")
    return any(importlib.util.find_spec(mod) is None for mod in required_modules)


def _check_non_empty_suite() -> None:
    if _deps_missing():
        _run(TEST_INSTALL_CMD)

    collect_out = _run(COLLECT_CMD)
    if re.search(r"collected\s+0\s+items", collect_out):
        raise ValidationError("I4 violation: collect-only reported zero tests")

    gate_out = _run(CANONICAL_GATE_CMD)
    if re.search(r"collected\s+0\s+items", gate_out):
        raise ValidationError("I4 violation: canonical gate reported zero tests")


def main() -> int:
    try:
        _check_top_level_permissions()
        _check_tool_versions()
        _check_canonical_workflow()
        _check_ssot_strings()
        _check_non_empty_suite()
    except ValidationError as exc:
        print(f"FAIL: {exc}")
        return 1

    print("PASS: Tri-Fix invariants validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
