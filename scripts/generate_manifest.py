#!/usr/bin/env python3
"""X1: Evidence freeze — generate SHA-256 manifest of all evidence artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate evidence manifest")
    parser.add_argument("--output", default="evidence_bundle_v1", help="Output dir name")
    args = parser.parse_args()

    evidence_dir = ROOT / "evidence"
    if not evidence_dir.exists():
        print("ERROR: evidence/ directory not found")
        return 1

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {"files": {}, "chain": []}
    chain_hash = hashlib.sha256(b"NFI_EVIDENCE_ROOT").hexdigest()

    files = sorted(evidence_dir.rglob("*"))
    file_count = 0
    for f in files:
        if f.is_dir():
            continue
        rel = str(f.relative_to(ROOT))
        file_hash = sha256_file(f)
        manifest["files"][rel] = file_hash  # type: ignore[index]
        # Chain: H_{i+1} = SHA256(H_i || file_hash)
        chain_hash = hashlib.sha256((chain_hash + file_hash).encode()).hexdigest()
        manifest["chain"].append({"file": rel, "hash": file_hash, "chain": chain_hash})  # type: ignore[union-attr]
        file_count += 1

    manifest["chain_root"] = chain_hash  # type: ignore[index]
    manifest["n_files"] = file_count  # type: ignore[index]

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Verify chain integrity
    verify_hash = hashlib.sha256(b"NFI_EVIDENCE_ROOT").hexdigest()
    for entry in manifest["chain"]:  # type: ignore[union-attr]
        verify_hash = hashlib.sha256((verify_hash + entry["hash"]).encode()).hexdigest()
        assert verify_hash == entry["chain"], f"Chain broken at {entry['file']}"

    print(f"Manifest: {file_count} files")
    print(f"Chain root: {chain_hash[:16]}...")
    print(f"SHA-256 chain: INTACT")
    print(f"Output: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
