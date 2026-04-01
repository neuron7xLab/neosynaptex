#!/usr/bin/env python3
"""Check canonical hash stability across representative inputs and repeated runs."""

from __future__ import annotations

import argparse
import subprocess


REPRESENTATIVE_INPUTS = [
    "examples/canonical_artifact.example.json",
    "tests/fixtures/artifact.valid.json",
    "tests/fixtures/evaluation-result.valid.json",
]


def hash_once(path: str) -> str:
    proc = subprocess.run(["python", "tools/canonicalize_and_hash.py", path], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip().splitlines()[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()

    for path in REPRESENTATIVE_INPUTS:
        digests = [hash_once(path) for _ in range(args.repeat)]
        assert len(set(digests)) == 1, (path, digests)

    print("CANONICAL_HASH_STABILITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
