"""Attest artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "artifacts" / "release"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _maybe(rel: str) -> dict[str, object] | None:
    path = ROOT / rel
    if not path.exists():
        return None
    return {"path": rel, "sha256": _sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    REL.mkdir(parents=True, exist_ok=True)
    target_paths = [
        "artifacts/release/release_manifest.json",
        "artifacts/release/final_evidence_index.md",
        "artifacts/release/sbom.spdx.json",
        "artifacts/release/sbom.sha256",
        "benchmarks/results/benchmark_core.json",
        "benchmarks/results/benchmark_quality.json",
        "artifacts/evidence/wave_7/validation/validation_summary.json",
        "artifacts/evidence/neurochem_controls/neurochem_controls_summary.json",
        "artifacts/evidence/wave_4/openapi_contract_report.json",
        "artifacts/evidence/wave_8/baseline_parity_report.json",
        "artifacts/evidence/wave_8/docs_drift_report.json",
        "artifacts/showcase/showcase_manifest.json",
        "artifacts/showcase/criticality_sweep/criticality_sweep_summary.json",
        "docs/contracts/showcase_run.etalon.json",
        "docs/contracts/showcase_run.etalon.sha256",
    ]
    artifacts = [item for item in (_maybe(rel) for rel in target_paths) if item is not None]
    lock_path = ROOT / "uv.lock"
    payload = {
        "attestation_version": "mfn-attestation-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(ROOT),
            "github_sha": os.environ.get("GITHUB_SHA", ""),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "lock_sha256": _sha256(lock_path) if lock_path.exists() else "",
        },
        "artifacts": artifacts,
    }
    (REL / "attestation.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
