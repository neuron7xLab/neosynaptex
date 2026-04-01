#!/usr/bin/env python3
"""Canonicalize a JSON file and compute its SHA-256 fingerprint."""
import argparse
import hashlib
import json
from pathlib import Path

def canonical_json_bytes(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--write-canonical", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    canonical_bytes = canonical_json_bytes(data)
    digest = hashlib.sha256(canonical_bytes).hexdigest()
    print(digest)
    if args.write_canonical:
        out_path = input_path.with_suffix(input_path.suffix + ".canonical.json")
        out_path.write_bytes(canonical_bytes)
        print(f"wrote {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
