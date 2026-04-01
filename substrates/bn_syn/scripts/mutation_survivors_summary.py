#!/usr/bin/env python3
"""Append surviving mutants section to GitHub step summary."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        print("❌ GITHUB_STEP_SUMMARY is not set.", file=sys.stderr)
        return 1

    survivors_path = Path("survived_mutants.txt")
    lines = ["## Surviving Mutants", ""]

    if survivors_path.exists() and survivors_path.stat().st_size > 0:
        with survivors_path.open(encoding="utf-8") as handle:
            content = handle.readlines()[:50]
        lines.append("```")
        lines.extend([line.rstrip("\n") for line in content])
        lines.append("```")
    else:
        lines.append("No surviving mutants!")

    with Path(summary_path).open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
