#!/usr/bin/env python3
"""Negative tests for canonicalization edge cases."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from canonicalize_and_hash import canonical_json_bytes


def must_fail_invalid_json() -> None:
    with tempfile.TemporaryDirectory(prefix="canon-neg-") as td:
        p = Path(td) / "bad.json"
        p.write_text('{"a": 1,}', encoding="utf-8")
        proc = subprocess.run(["python", "tools/canonicalize_and_hash.py", str(p)], check=False, capture_output=True, text=True)
        assert proc.returncode != 0, proc.stdout


def unicode_and_key_order_equivalence() -> None:
    a = {"β": "значення", "a": [3, 2, 1], "z": {"k": 1}}
    b = {"z": {"k": 1}, "a": [3, 2, 1], "β": "значення"}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def numeric_type_distinction() -> None:
    i = {"v": 1}
    f = {"v": 1.0}
    assert canonical_json_bytes(i) != canonical_json_bytes(f)


def main() -> int:
    must_fail_invalid_json()
    unicode_and_key_order_equivalence()
    numeric_type_distinction()
    print("CANONICALIZATION_NEGATIVE_CASES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
