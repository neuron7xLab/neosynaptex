#!/usr/bin/env python3
"""One command -> arxiv-ready submission package."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBMISSION_DIR = ROOT / "docs" / "submission"


def run(cmd: str) -> bool:
    result = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True)
    return result.returncode == 0


def build_supplementary() -> dict:
    ledger = json.loads((ROOT / "evidence" / "gamma_ledger.json").read_text())
    supp: dict = {
        "title": "Supplementary Materials",
        "gamma_table": {},
        "proof_chain_genesis": None,
    }
    for entry_id, entry in ledger["entries"].items():
        supp["gamma_table"][entry_id] = {
            "gamma": entry.get("gamma"),
            "ci": [entry.get("ci_low"), entry.get("ci_high")],
            "status": entry.get("status"),
        }
    x1_path = ROOT / "evidence_bundle_v1" / "manifest.json"
    if x1_path.exists():
        x1 = json.loads(x1_path.read_text())
        supp["proof_chain_genesis"] = x1.get("chain_root")
    return supp


def main() -> int:
    print("=== Building Submission Package ===\n")
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/4] Building evidence registry...")
    ok = run("python scripts/build_evidence_registry.py")
    print(f"  {'OK' if ok else 'WARN'}")

    print("[2/4] Generating figures...")
    ok = run("python scripts/generate_figures.py")
    print(f"  {'OK' if ok else 'WARN'}")

    print("[3/4] Verifying manuscript claims...")
    ok = run("python scripts/verify_manuscript_claims.py")
    if not ok:
        print("  FATAL: claims not verified")
        return 1

    print("[4/4] Building supplementary...")
    supp = build_supplementary()
    supp_path = SUBMISSION_DIR / "supplementary.json"
    supp_path.write_text(json.dumps(supp, indent=2, default=str))

    submission_files = {}
    for f in sorted(SUBMISSION_DIR.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(SUBMISSION_DIR))
            submission_files[rel] = hashlib.sha256(f.read_bytes()).hexdigest()

    genesis = "UNKNOWN"
    x1_path = ROOT / "evidence_bundle_v1" / "manifest.json"
    if x1_path.exists():
        genesis = json.loads(x1_path.read_text()).get("chain_root", "UNKNOWN")

    manifest = {
        "version": "1.0.0",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "proof_chain_genesis": genesis,
        "n_files": len(submission_files),
        "files": submission_files,
    }
    (SUBMISSION_DIR / "submission_manifest.json").write_text(json.dumps(manifest, indent=2))

    print("\n=== Submission Package Ready ===")
    print(f"  Directory: {SUBMISSION_DIR}")
    print(f"  Files: {len(submission_files)}")
    print(f"  Genesis: {genesis[:16]}...")
    for f in sorted(submission_files):
        print(f"    {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
