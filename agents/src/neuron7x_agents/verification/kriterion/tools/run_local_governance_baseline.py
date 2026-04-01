#!/usr/bin/env python3
"""Canonical local baseline contract checker/executor."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from governance_contract import BASELINE_DOC_END, BASELINE_DOC_START, load_registry, render_baseline_commands

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/PR_PREMERGE_ENGINEERING_CHECKLIST.md"

EXPECTED_EXIT_OVERRIDES = {
    "python tools/validate_json.py schemas/canonical-artifact.schema.json tests/fixtures/artifact.invalid.missing-valid-fingerprint.json": 1,
    "python tools/validate_json.py schemas/evaluation-result.schema.json tests/fixtures/evaluation-result.invalid.bad-gate.json": 1,
}

EXPECTED_MUTATED_TRACKED_FILES = {
    "python benchmark/benchmark_runner.py": {
        "benchmark/results/case-001.evaluation.json",
        "benchmark/results/case-002.evaluation.json",
        "benchmark/results/case-003.evaluation.json",
        "benchmark/results/case-004.evaluation.json",
        "benchmark/results/case-005.evaluation.json",
        "benchmark/results/case-006.evaluation.json",
        "benchmark/results/case-007.evaluation.json",
        "benchmark/results/case-008.evaluation.json",
        "benchmark/results/case-009.evaluation.json",
        "benchmark/results/case-010.evaluation.json",
        "benchmark/results/case_level_results.csv",
        "benchmark/metrics.json",
        "benchmark/logs/demo_benchmark_run.log",
    }
}


def tracked_dirty_files() -> set[str]:
    """Return tracked paths with staged or unstaged modifications."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return set()

    dirty: set[str] = set()
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        # porcelain v1 format: XY<space>PATH
        path = raw[3:] if len(raw) >= 4 else ""
        if path:
            dirty.add(path.strip())
    return dirty


def block_between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        return ""
    s = text.index(start) + len(start)
    e = text.index(end)
    return text[s:e].strip()


def checklist_commands() -> list[str]:
    text = CHECKLIST.read_text(encoding="utf-8")
    block = block_between(text, BASELINE_DOC_START, BASELINE_DOC_END)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    return [ln for ln in lines if not ln.startswith("```")]


def validate_execute_contract(commands: list[str]) -> None:
    command_set = set(commands)

    stale_exit_overrides = sorted(set(EXPECTED_EXIT_OVERRIDES) - command_set)
    if stale_exit_overrides:
        raise SystemExit(f"BASELINE_EXIT_OVERRIDE_STALE stale={stale_exit_overrides}")

    stale_dirty_policies = sorted(set(EXPECTED_MUTATED_TRACKED_FILES) - command_set)
    if stale_dirty_policies:
        raise SystemExit(f"BASELINE_DIRTY_POLICY_STALE stale={stale_dirty_policies}")


def assert_clean_tracked_tree() -> None:
    dirty = sorted(tracked_dirty_files())
    if dirty:
        raise SystemExit(f"BASELINE_REQUIRES_CLEAN_TREE dirty={dirty}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="execute baseline commands after contract check")
    args = ap.parse_args()

    expected = render_baseline_commands(load_registry(ROOT))
    actual = checklist_commands()
    if expected != actual:
        raise SystemExit(f"LOCAL_BASELINE_DRIFT expected={expected} actual={actual}")

    if args.execute:
        validate_execute_contract(actual)
        assert_clean_tracked_tree()
        for cmd in actual:
            before_dirty = tracked_dirty_files()
            proc = subprocess.run(["bash", "-lc", cmd], cwd=ROOT, check=False)
            expected_exit = EXPECTED_EXIT_OVERRIDES.get(cmd, 0)
            if proc.returncode != expected_exit:
                raise SystemExit(f"BASELINE_COMMAND_EXIT_MISMATCH cmd={cmd} expected={expected_exit} actual={proc.returncode}")

            after_dirty = tracked_dirty_files()
            new_dirty = after_dirty - before_dirty
            expected_dirty = EXPECTED_MUTATED_TRACKED_FILES.get(cmd, set())
            if not new_dirty.issubset(expected_dirty):
                raise SystemExit(f"BASELINE_COMMAND_DIRTY_SET_MISMATCH cmd={cmd} expected_subset_of={sorted(expected_dirty)} actual_dirty={sorted(new_dirty)}")
            if new_dirty:
                subprocess.run(["git", "checkout", "--", *sorted(new_dirty)], cwd=ROOT, check=True)

    print("LOCAL_BASELINE_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
