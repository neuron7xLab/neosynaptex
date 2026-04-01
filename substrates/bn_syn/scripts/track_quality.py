#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable


def run_command(cmd: str) -> tuple[int, str, str]:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def get_coverage() -> float | None:
    run_command("pytest -m 'not validation' --cov=src/bnsyn --cov-report=json -q 2>/dev/null")
    try:
        coverage_data = json.loads(Path("coverage.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return float(coverage_data["totals"]["percent_covered"])


def get_lint_issues() -> int | None:
    _, stdout, _ = run_command("ruff check . --output-format json 2>/dev/null")
    try:
        issues = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return None
    return int(len(issues))


def get_security_issues() -> int | None:
    _, stdout, _ = run_command("pip-audit --format json 2>/dev/null")
    try:
        data = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    counts: Iterable[int] = (len(v) for v in data.values() if isinstance(v, list))
    return int(sum(counts))


def main() -> None:
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "coverage_percent": get_coverage(),
        "lint_issues": get_lint_issues(),
        "security_issues": get_security_issues(),
        "test_results": "PASS" if run_command("pytest -m 'not validation' -q")[0] == 0 else "FAIL",
    }

    output_file = Path("metrics.json")
    output_file.write_text(json.dumps(metrics, indent=2))

    print("📊 Quality Metrics")
    coverage = metrics["coverage_percent"]
    if isinstance(coverage, (float, int)):
        print(f"  Coverage: {coverage:.1f}%")
    else:
        print("  Coverage: N/A")
    lint_issues = metrics["lint_issues"]
    if isinstance(lint_issues, int):
        print(f"  Lint issues: {lint_issues}")
    else:
        print("  Lint issues: N/A")
    security_issues = metrics["security_issues"]
    if isinstance(security_issues, int):
        print(f"  Security issues: {security_issues}")
    else:
        print("  Security issues: N/A")
    print(f"  Test results: {metrics['test_results']}")
    print(f"\n✅ Metrics saved to {output_file}")


if __name__ == "__main__":
    main()
