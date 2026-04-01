#!/usr/bin/env python3
"""CLI wrapper for pytest failure diagnostics aggregation."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate pytest failures from JUnit XML")
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--pytest-exit-code", required=True, type=int)
    parser.add_argument("--schema", type=Path, default=Path("schemas/pytest-failure-diagnostics.schema.json"))
    parser.add_argument("--annotations-file", type=Path, default=None)
    parser.add_argument("--emit-github-annotations", action="store_true")
    parser.add_argument("--max-annotations", type=int, default=10)
    parser.add_argument("--write-step-summary", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from bnsyn.qa.pytest_failure_diagnostics import PublicationOptions, generate_diagnostics

    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"]) if args.write_step_summary and os.environ.get("GITHUB_STEP_SUMMARY") else None
    publication = PublicationOptions(
        annotations_file=args.annotations_file,
        emit_github_annotations=args.emit_github_annotations,
        max_annotations=args.max_annotations,
        github_step_summary=summary_path,
    )
    generate_diagnostics(
        junit_xml=args.junit,
        output_json=args.output_json,
        output_md=args.output_md,
        pytest_exit_code=args.pytest_exit_code,
        schema_path=args.schema,
        log_file=args.log,
        publication=publication,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
