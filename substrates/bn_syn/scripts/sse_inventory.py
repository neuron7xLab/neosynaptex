from __future__ import annotations

import argparse
import json
from pathlib import Path

from sse_policy_load import load_and_validate

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/sse_sdo/01_scope")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    load_and_validate(ROOT / ".github" / "sse_sdo_fhe.yml")
    boundary_paths = sorted(
        [
            ".github/sse_sdo_fhe.yml",
            "scripts/xrun",
            "scripts/verify_integrity",
            "scripts/sse_policy_load.py",
            "scripts/sse_inventory.py",
            "scripts/sse_drift_check.py",
            "scripts/sse_gate_runner.py",
            "scripts/sse_proof_index.py",
            "scripts/sse_safety_gate",
            "tests/test_sse_policy_schema_contract.py",
            "tests/test_policy_to_execution_contract.py",
            "tests/test_required_checks_contract.py",
            "tests/test_ssot_alignment_contract.py",
            "tests/test_workflow_integrity_contract.py",
            ".github/workflows/sse-sdo-fhe-gate.yml",
        ]
    )
    dep_graph = {"nodes": boundary_paths, "edges": []}
    interface_registry = {
        "interfaces": [
            {"path": p, "exists": (ROOT / p).exists(), "entrypoint": p.startswith("scripts/") or p.startswith(".github/workflows/")}
            for p in boundary_paths
        ]
    }
    (out / "SUBSYSTEM_BOUNDARY.md").write_text(
        "# SUBSYSTEM_BOUNDARY\n\n- name: sse-sdo-fhe\n- entrypoints: scripts/xrun, scripts/verify_integrity, scripts/sse_gate_runner.py\n",
        encoding="utf-8",
    )
    (out / "DEP_GRAPH.json").write_text(json.dumps(dep_graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "INTERFACE_REGISTRY.json").write_text(json.dumps(interface_registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
