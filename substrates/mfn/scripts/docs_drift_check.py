"""Docs drift check."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS: dict[str, list[str]] = {
    "README.md": [
        "SimulationSpec",
        "diagnose",
        "causal",
    ],
    "docs/ARCHITECTURE.md": [
        "single canonical owner of the simulation step",
        "numerics/update_rules.py",
        "compatibility-only",
    ],
    "docs/LOCAL_RUNBOOK.md": ["showcase-generation", "baseline-parity", "attestation"],
    "docs/API.md": ["openapi.v2.json", "neuromodulation"],
    "docs/DATA_MODEL.md": ["NeuromodulationSpec", "profile_id", "evidence_version"],
    "docs/templates/VALIDATION_REPORT_TEMPLATE.md": [
        "showcase_generation",
        "baseline_parity",
        "artifact_attestation",
    ],
}


def main() -> int:
    failures: list[dict[str, object]] = []
    for rel, patterns in CHECKS.items():
        path = ROOT / rel
        if not path.exists():
            failures.append({"path": rel, "missing": patterns})
            continue
        text = path.read_text(encoding="utf-8")
        missing = [pattern for pattern in patterns if pattern not in text]
        if missing:
            failures.append({"path": rel, "missing": missing})
    payload = {"ok": not failures, "failures": failures}
    out = ROOT / "artifacts" / "evidence" / "wave_8" / "docs_drift_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
