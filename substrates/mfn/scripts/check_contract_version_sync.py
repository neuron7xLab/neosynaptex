#!/usr/bin/env python3
"""CI gate: verify all contract versions match pyproject.toml.

Exit 0 if all versions match, exit 1 otherwise.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def get_pyproject_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text().splitlines():
        if line.startswith("version"):
            return line.split('"')[1]
    raise RuntimeError("version not found in pyproject.toml")


def main() -> int:
    version = get_pyproject_version()
    print(f"pyproject.toml version: {version}")

    checks = [
        ("docs/contracts/claims_manifest.json", "engine_version"),
        ("docs/contracts/openapi.v1.json", "info.version"),
        ("docs/contracts/openapi.v2.json", "info.version"),
    ]

    errors = 0
    for path, key_path in checks:
        fpath = ROOT / path
        if not fpath.exists():
            print(f"  SKIP  {path} (not found)")
            continue

        data = json.loads(fpath.read_text())
        keys = key_path.split(".")
        val = data
        for k in keys:
            val = val.get(k, {})

        if val == version:
            print(f"  OK    {path} → {val}")
        else:
            print(f"  FAIL  {path} → {val} (expected {version})")
            errors += 1

    if errors:
        print(f"\n{errors} version mismatch(es) found.")
        return 1
    print("\nAll contract versions in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
