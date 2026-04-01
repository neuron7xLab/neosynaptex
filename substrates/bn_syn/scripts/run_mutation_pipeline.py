#!/usr/bin/env python3
"""Run mutmut with crash/survivor-aware fail-closed semantics."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _run_results() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["mutmut", "results"],
        capture_output=True,
        text=True,
        check=False,
    )


def _has_valid_results_output(result: subprocess.CompletedProcess[str]) -> bool:
    return bool(result.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute mutation run and export artifacts")
    parser.add_argument(
        "--paths-to-mutate",
        default=(
            "src/bnsyn/neuron/adex.py,"
            "src/bnsyn/plasticity/stdp.py,"
            "src/bnsyn/plasticity/three_factor.py,"
            "src/bnsyn/temperature/schedule.py"
        ),
        help="Comma-separated paths passed to mutmut --paths-to-mutate",
    )
    parser.add_argument(
        "--runner",
        default='pytest -x -q -m "not validation and not property and not benchmark"',
        help="mutmut runner command",
    )
    parser.add_argument("--tests-dir", default="tests", help="mutmut tests directory")
    parser.add_argument("--results-file", default="mutation_results.txt", type=Path)
    parser.add_argument("--results-stderr-file", default="mutation_results.stderr.txt", type=Path)
    parser.add_argument("--survivors-file", default="survived_mutants.txt", type=Path)
    args = parser.parse_args(argv)

    run_proc = subprocess.run(
        [
            "mutmut",
            "run",
            "--paths-to-mutate",
            args.paths_to_mutate,
            "--tests-dir",
            args.tests_dir,
            "--runner",
            args.runner,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    results_proc = _run_results()
    if results_proc.returncode != 0 or not _has_valid_results_output(results_proc):
        print("❌ mutmut results failed; mutation run treated as crash.", file=sys.stderr)
        print(run_proc.stdout, file=sys.stderr)
        print(run_proc.stderr, file=sys.stderr)
        print(results_proc.stdout, file=sys.stderr)
        print(results_proc.stderr, file=sys.stderr)
        return 1

    _write_text(args.results_file, results_proc.stdout)
    _write_text(args.results_stderr_file, results_proc.stderr)

    survivors_proc = subprocess.run(
        ["mutmut", "show", "--status", "survived"],
        capture_output=True,
        text=True,
        check=False,
    )
    _write_text(args.survivors_file, survivors_proc.stdout)

    if run_proc.returncode != 0:
        print("ℹ️ mutmut run returned non-zero, but results are present; continuing to score gate.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
