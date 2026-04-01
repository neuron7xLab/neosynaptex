from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SUITE_REPORT = ROOT / "audit_suite_report.json"
ATTACK_PATHS = ROOT / "attack_paths_graph.json"
PROOF_INDEX = ROOT / "proof_bundle" / "index.json"
READINESS_REPORT = ROOT / "readiness_report.json"
READINESS_SUMMARY = ROOT / "readiness_summary.md"
AUDIT_REPRO = ROOT / "audit_reproducibility.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _compute_confidence_per_module(modules: dict[str, Any]) -> dict[str, float]:
    return {
        name: round(float(payload.get("confidence_0_1", 0.0)), 4)
        for name, payload in sorted(modules.items())
    }


def _compute_adjusted_risk_per_module(modules: dict[str, Any]) -> dict[str, float]:
    adjusted: dict[str, float] = {}
    for name, payload in sorted(modules.items()):
        risk = float(payload.get("score_0_100", 0.0))
        confidence = float(payload.get("confidence_0_1", 0.0))
        adjusted[name] = round(risk * confidence, 4)
    return adjusted



def _normalize_attack_paths() -> None:
    payload = _load_json(ATTACK_PATHS)
    if "chains" in payload and "minimal_cut_sets" in payload:
        return

    privilege_chains = payload.get("privilege_chains", [])
    chains = []
    minimal_cut_sets = []
    for item in privilege_chains:
        chain = item.get("chain", [])
        chains.append(
            {
                "path": chain,
                "feasibility_score_0_100": item.get("feasibility_score_0_100", 0),
            }
        )
        for cut_set in item.get("minimal_cut_sets", []):
            minimal_cut_sets.append(cut_set)

    normalized = {
        "meta": payload.get("meta", {}),
        "nodes": payload.get("nodes", []),
        "edges": payload.get("edges", []),
        "chains": chains,
        "minimal_cut_sets": minimal_cut_sets,
    }
    ATTACK_PATHS.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def build() -> None:
    _normalize_attack_paths()
    source = _load_json(AUDIT_SUITE_REPORT)
    modules = source["modules"]
    confidence_per_module = _compute_confidence_per_module(modules)
    adjusted_risk = _compute_adjusted_risk_per_module(modules)

    evidence_strength_values = [
        float(payload.get("evidence_strength_index", 0.0)) for payload in modules.values()
    ]
    evidence_strength_index = round(
        sum(evidence_strength_values) / len(evidence_strength_values), 4
    ) if evidence_strength_values else 0.0

    report: dict[str, Any] = {
        "meta": source["meta"],
        "representator": source["representator"],
        "modules": modules,
        "repo_scale_classification": source["meta"]["repo_scale_classification"],
        "depth_plan": source["meta"]["depth_level_per_module"],
        "time_budget_allocation": source["meta"]["time_budget_allocation_strategy"],
        "confidence_per_module": confidence_per_module,
        "adjusted_risk": adjusted_risk,
        "residual_uncertainty_index": source["executive"]["residual_uncertainty_index_0_100"],
        "evidence_strength_index": evidence_strength_index,
        "security_maturity_level": source["executive"]["security_maturity_level_1_5"],
        "executive_decision_support_matrix": source["executive"][
            "executive_decision_support_matrix"
        ],
        "resource_allocation_optimizer": source["executive"][
            "resource_allocation_optimizer"
        ],
        "cross_module_consistency": source["cross_module_consistency"],
        "proof_bundle_index": source["proof_bundle_index"],
    }

    READINESS_REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    matrix = source.get("executive", {}).get("executive_decision_support_matrix", [])
    top_blockers = [item for item in matrix if item.get("decision") == "Fix Now"][:5]
    blocker_line = "; ".join(item.get("risk_title", "unknown") for item in top_blockers)
    summary = (
        f"Readiness {round(100 - source['executive']['weighted_executive_risk_index_0_100'])}% with "
        f"audit_quality_score {modules['M0_audit_integrity_control']['audit_quality_score_0_100']} and "
        f"confidence {source['executive']['confidence_0_1']:.2f}. "
        f"Top blockers: {blocker_line if blocker_line else 'none recorded'}."
    )
    READINESS_SUMMARY.write_text(summary + "\n", encoding="utf-8")

    proof = _load_json(PROOF_INDEX)
    audit_repro = {
        "audit_hash": source["meta"]["audit_hash_sha256"],
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "toolchain_fingerprint_artifact": source["meta"]["toolchain_fingerprint_artifact"],
        "artifact_hashes": {
            "audit_suite_report.json": _sha256(AUDIT_SUITE_REPORT),
            "readiness_report.json": _sha256(READINESS_REPORT),
            "attack_paths_graph.json": _sha256(ATTACK_PATHS),
            "proof_bundle/index.json": _sha256(PROOF_INDEX),
        },
        "proof_bundle_entries": len(proof),
        "deterministic_replay_steps": [
            "python scripts/build_readiness_artifacts.py",
            "pytest -q tests/test_readiness_artifact_schemas.py tests/test_audit_suite_artifacts.py",
        ],
    }
    AUDIT_REPRO.write_text(
        json.dumps(audit_repro, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
