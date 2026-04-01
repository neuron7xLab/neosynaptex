#!/usr/bin/env python3
"""Self-Check — single command that validates EVERYTHING.

Runs all gates in sequence. Any failure = non-zero exit.
This is the canonical "is the project healthy?" command.

Usage:
    python scripts/selfcheck.py          # full check
    python scripts/selfcheck.py --quick  # skip slow checks
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

VENV = ".venv/bin/python"


def _run(name: str, cmd: list[str], timeout: int = 300) -> tuple[bool, str]:
    """Run a check and return (passed, output)."""
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        elapsed = time.perf_counter() - t0
        passed = result.returncode == 0
        output = result.stdout + result.stderr
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name} ({elapsed:.1f}s)")
        return passed, output
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {name}")
        return False, "timeout"


def main() -> None:
    quick = "--quick" in sys.argv
    results: dict[str, bool] = {}

    print("MFN Self-Check\n" + "=" * 50)

    # 1. Syntax check (instant)
    ok, _ = _run("Python syntax", [VENV, "-c", "import mycelium_fractal_net"])
    results["syntax"] = ok

    # 2. Format
    ok, _ = _run("Code format", [VENV, "-m", "ruff", "format", "--check", "src/", "tests/"])
    results["format"] = ok

    # 3. Import contracts
    ok, _ = _run("Import contracts", [".venv/bin/lint-imports"])
    results["import_contracts"] = ok

    # 4. Contract validation
    ok, _ = _run("Contract validation", [VENV, "scripts/validate_contracts.py"])
    results["contracts"] = ok

    # 5. mypy strict
    ok, _ = _run(
        "mypy strict (core + bio)",
        [
            VENV,
            "-m",
            "mypy",
            "src/mycelium_fractal_net/core/",
            "src/mycelium_fractal_net/analytics/",
            "src/mycelium_fractal_net/neurochem/",
            "src/mycelium_fractal_net/intervention/",
            "src/mycelium_fractal_net/bio/",
            "--strict",
            "--ignore-missing-imports",
            "--exclude",
            "(turing|federated|stdp)\\.py",
        ],
    )
    results["mypy_strict"] = ok

    # 6. Architectural invariants
    ok, _ = _run(
        "Architectural invariants",
        [
            VENV,
            "-m",
            "pytest",
            "tests/test_architectural_invariants.py",
            "-v",
            "--timeout=60",
        ],
    )
    results["invariants"] = ok

    # 6b. Docs↔runtime (examples must execute)
    ok, _ = _run(
        "Docs examples",
        [VENV, "-m", "pytest", "tests/test_docs_examples.py", "-v", "--timeout=60"],
    )
    results["docs_examples"] = ok

    # 6c. Golden hashes
    ok, _ = _run(
        "Golden hashes",
        [VENV, "-m", "pytest", "tests/test_golden_hashes.py", "-v", "--timeout=60"],
    )
    results["golden_hashes"] = ok

    # 7. Core tests
    ok, _ = _run(
        "Core tests",
        [
            VENV,
            "-m",
            "pytest",
            "tests/",
            "--ignore=tests/ml/",
            "-q",
            "--timeout=120",
            "-x",
        ],
        timeout=300,
    )
    results["core_tests"] = ok

    if not quick:
        # 8. Full tests
        ok, _ = _run(
            "Full tests",
            [
                VENV,
                "-m",
                "pytest",
                "tests/",
                "-q",
                "--timeout=300",
            ],
            timeout=600,
        )
        results["full_tests"] = ok

        # 9. Scientific validation
        ok, _ = _run("Scientific validation", [VENV, "validation/scientific_validation.py"])
        results["scientific"] = ok

        # 10. Reproducibility
        ok, _ = _run("Reproducibility", [VENV, "scripts/generate_reproducibility_matrix.py"])
        results["reproducibility"] = ok

        # 11. Benchmarks
        ok, _ = _run("Benchmarks", [VENV, "benchmarks/benchmark_core.py"])
        results["benchmarks"] = ok

        # 12. Interface parity
        ok, _ = _run("Interface parity", [VENV, "scripts/interface_parity_check.py"])
        results["parity"] = ok

        # 13. Security
        ok, _ = _run(
            "Bandit security",
            [
                VENV,
                "-m",
                "bandit",
                "-r",
                "src/",
                "-q",
                "--severity-level",
                "medium",
            ],
        )
        results["security"] = ok

    # Summary
    print("\n" + "=" * 50)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    report = {
        "schema_version": "mfn-selfcheck-v1",
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "results": {k: "PASS" if v else "FAIL" for k, v in results.items()},
    }

    out = Path("artifacts/selfcheck_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    if failed:
        print(f"\nFAILED: {failed}/{total} checks")
        for name, ok in results.items():
            if not ok:
                print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"\nALL PASS: {passed}/{total} checks")


if __name__ == "__main__":
    main()
