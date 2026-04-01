#!/usr/bin/env python3
"""Emit canonical mutation CI outputs and GitHub summary."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from scripts.mutation_counts import (
    MutationAssessment,
    assess_mutation_gate,
    load_mutation_baseline,
    read_mutation_counts,
    render_ci_summary_markdown,
    render_github_output_lines,
)


def write_github_output(path: Path, assessment: MutationAssessment) -> None:
    with path.open("a", encoding="utf-8") as output:
        output.write(render_github_output_lines(assessment))


def _render_not_evaluated(reason: str) -> str:
    return (
        "## Mutation Testing Results\n\n"
        "**Gate Status:** ⚠️ NOT EVALUATED\n\n"
        f"Reason: `{reason}`\n\n"
        "Use `python -m scripts.check_mutation_score --strict` as the enforcement gate.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate canonical mutation CI outputs and summary"
    )
    parser.add_argument(
        "--baseline",
        default="quality/mutation_baseline.json",
        type=Path,
        help="Path to mutation baseline JSON",
    )
    parser.add_argument(
        "--write-output",
        action="store_true",
        help="Write canonical metrics to $GITHUB_OUTPUT",
    )
    parser.add_argument(
        "--write-summary",
        action="store_true",
        help="Write markdown report to $GITHUB_STEP_SUMMARY",
    )
    args = parser.parse_args()

    if not args.write_output and not args.write_summary:
        print(
            "❌ No output target selected. Use --write-output and/or --write-summary.",
            file=sys.stderr,
        )
        return 1

    output_path: Path | None = None
    summary_path: Path | None = None

    if args.write_output:
        output_path_raw = os.environ.get("GITHUB_OUTPUT")
        if not output_path_raw:
            print("❌ GITHUB_OUTPUT is not set.", file=sys.stderr)
            return 1
        output_path = Path(output_path_raw)

    if args.write_summary:
        summary_path_raw = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_path_raw:
            print("❌ GITHUB_STEP_SUMMARY is not set.", file=sys.stderr)
            return 1
        summary_path = Path(summary_path_raw)

    assessment: MutationAssessment | None = None
    not_evaluated_reason = ""

    baseline = None
    try:
        baseline = load_mutation_baseline(args.baseline)
    except FileNotFoundError as exc:
        not_evaluated_reason = f"baseline file not found: {exc}"
    except (KeyError, ValueError, TypeError) as exc:
        not_evaluated_reason = f"invalid baseline payload: {exc}"

    if baseline is not None:
        try:
            counts = read_mutation_counts()
            assessment = assess_mutation_gate(counts, baseline)
        except FileNotFoundError as exc:
            not_evaluated_reason = f"mutmut executable not found: {exc}"
        except subprocess.CalledProcessError as exc:
            not_evaluated_reason = f"mutmut result-ids failed: {exc}"

    try:
        if output_path is not None and assessment is not None:
            write_github_output(output_path, assessment)

        if summary_path is not None:
            if assessment is None:
                with summary_path.open("a", encoding="utf-8") as summary_file:
                    summary_file.write(_render_not_evaluated(not_evaluated_reason))
            else:
                markdown = render_ci_summary_markdown(assessment)
                with summary_path.open("a", encoding="utf-8") as summary_file:
                    summary_file.write(markdown)
    except OSError as exc:
        print(f"❌ Failed to write CI artifacts: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
