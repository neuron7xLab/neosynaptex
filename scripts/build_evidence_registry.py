#!/usr/bin/env python3
"""Build unified evidence registry from all substrate evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def collect_artifacts() -> list[dict]:
    artifacts: list[dict] = []

    ledger_path = ROOT / "evidence" / "gamma_ledger.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        ledger_hash = sha256_file(ledger_path)
        for entry_id, entry in ledger.get("entries", {}).items():
            artifacts.append(
                {
                    "id": f"gamma:{entry_id}",
                    "type": "gamma_value",
                    "substrate": entry_id,
                    "gamma": entry.get("gamma"),
                    "status": entry.get("status"),
                    "locked": entry.get("locked", False),
                    "source_file": "evidence/gamma_ledger.json",
                    "sha256": ledger_hash,
                }
            )

    for bundle_file in sorted(ROOT.glob("evidence/proof_*.json")):
        try:
            bundle = json.loads(bundle_file.read_text())
            artifacts.append(
                {
                    "id": f"proof:{bundle_file.stem}",
                    "type": "proof_bundle",
                    "source_file": str(bundle_file.relative_to(ROOT)),
                    "sha256": sha256_file(bundle_file),
                    "chain_hash": bundle.get("chain", {}).get("self_hash"),
                }
            )
        except Exception:
            pass

    for manifest_dir in ["evidence_bundle_v1", "evidence_bundle_v2"]:
        x1_path = ROOT / manifest_dir / "manifest.json"
        if x1_path.exists():
            x1 = json.loads(x1_path.read_text())
            artifacts.append(
                {
                    "id": f"manifest:{manifest_dir}",
                    "type": "genesis_manifest",
                    "chain_root": x1.get("chain_root"),
                    "n_files": x1.get("n_files"),
                    "source_file": f"{manifest_dir}/manifest.json",
                    "sha256": sha256_file(x1_path),
                }
            )

    for fig_file in sorted((ROOT / "figures").rglob("*.json")):
        artifacts.append(
            {
                "id": f"figure:{fig_file.stem}",
                "type": "analysis_artifact",
                "source_file": str(fig_file.relative_to(ROOT)),
                "sha256": sha256_file(fig_file),
            }
        )

    return artifacts


def main() -> int:
    artifacts = collect_artifacts()

    registry = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_artifacts": len(artifacts),
        "registry_hash": sha256_str(json.dumps(artifacts, sort_keys=True, default=str)),
        "artifacts": {a["id"]: a for a in artifacts},
    }

    out_path = ROOT / "evidence" / "registry.json"
    out_path.write_text(json.dumps(registry, indent=2, default=str))

    print("=== Evidence Registry Built ===")
    print(f"  Artifacts: {registry['n_artifacts']}")
    print(f"  Registry hash: {registry['registry_hash'][:16]}...")
    print(f"  Output: {out_path}")

    types = Counter(a["type"] for a in registry["artifacts"].values())
    for t, n in sorted(types.items()):
        print(f"  {t}: {n}")

    print("\n  Registry: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
