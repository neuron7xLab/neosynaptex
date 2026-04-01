#!/usr/bin/env python3
"""Verify SHA-256 values from MANIFEST.json."""
import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_json)
    root = Path(args.root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for rel, expected in manifest.items():
        if rel == "MANIFEST.json":
            continue
        path = root / rel
        if not path.exists():
            print(f"INTEGRITY_VIOLATION {rel} | expected={expected} | actual=MISSING")
            print("DEPLOY BLOCKED — repository state is tainted")
            return 2
        actual = sha256_file(path)
        if actual != expected:
            print(f"INTEGRITY_VIOLATION {rel} | expected={expected} | actual={actual}")
            print("DEPLOY BLOCKED — repository state is tainted")
            return 2
    print("MANIFEST_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
