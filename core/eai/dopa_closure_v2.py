from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate

from core.eai.dopa_artifacts import claim_artifact_name, sha256_file, write_json
from core.eai.dopa_budget import BudgetLedger
from core.eai.dopa_construct_gate import ConstructContext, validate_construct_context
from core.eai.dopa_controls import run_controls
from core.eai.dopa_types import ClaimSignal, FinalStatus, RouteMode

_SHA40 = re.compile(r"^[a-f0-9]{40}$")


def _git_head_sha() -> str:
    env_sha = os.getenv("COMMIT_SHA") or os.getenv("GITHUB_SHA")
    if env_sha and _SHA40.fullmatch(env_sha.strip()):
        return env_sha.strip()
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "UNSTAMPED:dopa_closure_v2"


class DopaClosureV2Allocator:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        schema = json.loads(Path("schemas/dopa_closure_v2_config.schema.json").read_text(encoding="utf-8"))
        validate(self.config, schema)
        self.config_hash = hashlib.sha256(self.config_path.read_bytes()).hexdigest()

    def priority_of_verification(self, claim: ClaimSignal) -> float:
        w = self.config["priority_gate"]["weights"]
        drive = (
            w["prediction_error"] * claim.prediction_error
            + w["uncertainty"] * claim.uncertainty
            + w["novelty"] * claim.novelty
            + w["evidence_risk"] * claim.evidence_risk
            + w["reversibility"] * (1.0 - claim.reversibility)
        )
        center = float(self.config["priority_gate"]["load_center"])
        spread = float(self.config["priority_gate"]["load_spread"])
        return max(0.0, float(drive * max(0.0, 1.0 - ((claim.load - center) / spread) ** 2)))


def run_allocator_full_path(config_path: str | Path, claims: list[ClaimSignal], output_root: str | Path, construct_context: ConstructContext) -> dict[str, Any]:
    allocator = DopaClosureV2Allocator(config_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(output_root) / "runs" / run_id
    output.mkdir(parents=True, exist_ok=True)
    verdict = validate_construct_context(construct_context)
    write_json(output / "construct_gate.json", asdict(verdict))
    (output / "config.sha256").write_text(allocator.config_hash + "\n", encoding="utf-8")
    (output / "config.yaml").write_text(Path(config_path).read_text(encoding="utf-8"), encoding="utf-8")
    if not verdict.admissible:
        final = {"run_id": run_id, "final_verdict": verdict.verdict, "failure_reasons": verdict.reasons, "config_hash": allocator.config_hash, "commit_sha": _git_head_sha(), "routes": []}
        write_json(output / "final_verdict.json", final)
        return final

    cfg = allocator.config
    t = cfg["priority_gate"]["thresholds"]
    ledger = BudgetLedger.create(float(cfg["budget"]["envelope"]), float(cfg["budget"].get("probe_tax", 0.0)))
    routes, priorities, artifact_hashes = [], [], {}
    for claim in claims:
        priority = allocator.priority_of_verification(claim)
        priorities.append(priority)
        route_mode: RouteMode = (
            RouteMode.REJECT if claim.evidence_risk >= t["reject_evidence_risk"] else
            RouteMode.ESCALATE if priority >= t["escalate"] else
            RouteMode.VERIFY if priority >= t["verify"] else
            RouteMode.CHEAP_TRIAGE if priority >= t["triage"] else
            RouteMode.QUARANTINE
        )
        step = ledger.apply(float(cfg["budget"]["action_costs"][route_mode.value]), float(cfg["budget"]["action_costs"][RouteMode.QUARANTINE.value]))
        verification_result = "not_run"
        default_status = {
            RouteMode.REJECT: FinalStatus.REJECTED,
            RouteMode.ESCALATE: FinalStatus.ESCALATE,
            RouteMode.VERIFY: FinalStatus.VERIFY,
            RouteMode.CHEAP_TRIAGE: FinalStatus.CHEAP_TRIAGE,
            RouteMode.QUARANTINE: FinalStatus.QUARANTINED,
        }
        final_status: FinalStatus = default_status[route_mode]
        quarantine_reason = None
        if step.overspend:
            route_mode, final_status, quarantine_reason = RouteMode.QUARANTINE, FinalStatus.QUARANTINED, "INSUFFICIENT_BUDGET"
        elif route_mode == RouteMode.VERIFY:
            verification_result = "pass" if claim.evidence_risk <= t["close_evidence_risk_max"] else "inconclusive"
            final_status = FinalStatus.CLOSED if verification_result == "pass" else FinalStatus.QUARANTINED

        claim_dir = output / "claims" / claim.claim_id
        artifact = claim_artifact_name(route_mode.value, final_status.value)
        route_doc = {"claim_id": claim.claim_id, "route_mode": route_mode.value, "epistemic_status": claim.epistemic_status, "final_status": final_status.value, "priority_of_verification": priority, "verification_result": verification_result, "quarantine_reason": quarantine_reason, "budget": asdict(step), "config_hash": allocator.config_hash}
        write_json(claim_dir / artifact, route_doc)
        route_doc["verification_artifact_hash"] = sha256_file(claim_dir / artifact) if final_status == FinalStatus.CLOSED else None
        write_json(claim_dir / "route.json", route_doc)
        artifact_hashes[f"{claim.claim_id}/{artifact}"] = sha256_file(claim_dir / artifact)
        routes.append(route_doc)

    controls_doc = asdict(run_controls(claims, priorities, seed=int(cfg["negative_controls"]["random_routing_seed"])))
    write_json(output / "controls.json", controls_doc)
    final_verdict = "ADMISSIBLE" if controls_doc["passed"] else "INADMISSIBLE"
    result = {"run_id": run_id, "commit_sha": _git_head_sha(), "final_verdict": final_verdict, "failure_reasons": [] if final_verdict == "ADMISSIBLE" else ["controls_failed"], "config_hash": allocator.config_hash, "construct_gate": asdict(verdict), "controls": controls_doc, "budget_ledger": ledger.snapshot(), "routes": routes, "artifact_hashes": artifact_hashes, "provenance": {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "config_path": str(config_path)}}
    write_json(output / "budget_ledger.json", result["budget_ledger"])
    write_json(output / "final_verdict.json", result)
    return result
