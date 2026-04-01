"""Validate required traceability table structure in docs/TRACEABILITY.md."""

from __future__ import annotations

import re
from pathlib import Path

TRACEABILITY_PATH = Path("docs/TRACEABILITY.md")
REQUIRED_COLUMNS = ["spec", "schema", "code", "test", "doc", "status"]
ALLOWED_STATUS = {"OK", "GAP", "BLOCKED"}


def _extract_table(text: str) -> list[str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("| spec | schema | code | test | doc | status |"):
            table: list[str] = []
            for row in lines[i:]:
                if not row.strip().startswith("|"):
                    break
                table.append(row.rstrip())
            return table
    return []


def main() -> int:
    if not TRACEABILITY_PATH.exists():
        raise SystemExit("TRACEABILITY_MISSING: docs/TRACEABILITY.md")

    table = _extract_table(TRACEABILITY_PATH.read_text(encoding="utf-8"))
    if len(table) < 3:
        raise SystemExit("TRACEABILITY_TABLE_MISSING_OR_EMPTY")

    header = [cell.strip().lower() for cell in table[0].split("|")[1:-1]]
    if header != REQUIRED_COLUMNS:
        raise SystemExit(f"TRACEABILITY_BAD_HEADER: expected {REQUIRED_COLUMNS}, got {header}")

    for idx, row in enumerate(table[2:], start=3):
        cells = [cell.strip() for cell in row.split("|")[1:-1]]
        if len(cells) != len(REQUIRED_COLUMNS):
            raise SystemExit(f"TRACEABILITY_BAD_ROW_COL_COUNT:L{idx}")
        if any(not cell for cell in cells):
            raise SystemExit(f"TRACEABILITY_EMPTY_CELL:L{idx}")
        if cells[-1] not in ALLOWED_STATUS:
            raise SystemExit(f"TRACEABILITY_BAD_STATUS:L{idx}:{cells[-1]}")
        for c in cells[:-1]:
            if c != "—" and not re.match(r"^[A-Za-z0-9_./\-]+$", c):
                raise SystemExit(f"TRACEABILITY_BAD_PATH_TOKEN:L{idx}:{c}")

    print("TRACEABILITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
