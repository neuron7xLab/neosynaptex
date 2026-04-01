"""Validate test collection and gate-suite integrity."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

CANONICAL_GATE_CMD = ["make", "test-gate"]
GATE_MARKER_EXPRESSION = "not (validation or property)"
COLLECT_TIMEOUT_S = 300
GATE_TIMEOUT_S = 600


class ValidationError(RuntimeError):
    """Validation failure."""


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _fail(message: str) -> None:
    raise ValidationError(message)


def _extract_collected_count(pytest_output: str) -> int:
    match = re.search(r"(\d+) tests collected", pytest_output)
    if match:
        return int(match.group(1))
    total = 0
    for line in pytest_output.splitlines():
        node_match = re.search(r":\s*(\d+)\s*$", line)
        if node_match:
            total += int(node_match.group(1))
    return total


def _scan_test_quality() -> list[str]:
    failures: list[str] = []
    for path in Path("tests").rglob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\s*assert\s+True\s*(?:#.*)?$", text):
            failures.append(f"assert True found: {path}")
        if re.search(r"(?m)^\s*#\s*def\s+test_", text):
            failures.append(f"commented-out test found: {path}")
    return failures


def _scan_gate_skip_xfail() -> list[str]:
    failures: list[str] = []
    for path in Path("tests").rglob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        if "@pytest.mark.validation" in text or "@pytest.mark.property" in text:
            continue
        if re.search(r"@pytest\.mark\.skip\(", text):
            failures.append(f"unconditional @skip in gate-scope file: {path}")
        if re.search(r"@pytest\.mark\.xfail", text):
            failures.append(f"xfail in gate-scope file: {path}")
    return failures


def main() -> int:
    collect = _run(["python", "-m", "pytest", "--collect-only", "-q"], COLLECT_TIMEOUT_S)
    if collect.returncode != 0:
        _fail(f"collection failed\n{collect.stdout}\n{collect.stderr}")

    gate_collect = _run(["python", "-m", "pytest", "--collect-only", "-q", "-m", GATE_MARKER_EXPRESSION], COLLECT_TIMEOUT_S)
    if gate_collect.returncode != 0:
        _fail(f"gate collection failed\n{gate_collect.stdout}\n{gate_collect.stderr}")
    if _extract_collected_count(f"{gate_collect.stdout}\n{gate_collect.stderr}") < 1:
        _fail("gate suite selects zero tests")

    gate = _run(CANONICAL_GATE_CMD, GATE_TIMEOUT_S)
    if gate.returncode != 0:
        _fail(f"gate failed\n{gate.stdout}\n{gate.stderr}")

    issues = _scan_test_quality() + _scan_gate_skip_xfail()
    if issues:
        _fail("\n".join(issues))

    print("validate_test_integrity: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validate_test_integrity: FAIL: {exc}")
        raise SystemExit(1)
