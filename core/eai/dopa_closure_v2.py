from __future__ import annotations

import os
import re
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.eai.dopa_artifacts import claim_artifact_name, sha256_file, write_json
from core.eai.dopa_budget import BudgetLedger
from core.eai.dopa_construct_gate import ConstructContext, validate_construct_context
from core.eai.dopa_controls import run_controls
from core.eai.dopa_result import Err, Ok, Result
from core.eai.dopa_runtime_config import load_and_validate_config
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


def _run_id() -> str:
    return os.getenv("DOPA_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class DopaClosureV2Allocator:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        loaded = load_and_validate_config(self.config_path, Path("schemas/dopa_closure_v2_config.schema.json"))
        if isinstance(loaded, Err):
            raise ValueError(loaded.reason)
        self.config = loaded.value.payload
        self.config_hash = loaded.value.config_hash

    def priority_of_verification(self, claim: ClaimSignal, budget_ratio: float = 1.0) -> float:
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
        eps = 1e-9
        load_gate = max(0.0, 1.0 - ((claim.load - center) / (spread + eps)) ** 2)
        scarcity_boost = (1.0 - max(0.0, min(1.0, budget_ratio))) * claim.prediction_error * 0.35
        return max(0.0, float((drive + scarcity_boost) * load_gate))


def run_allocator_full_path(config_path: str | Path, claims: list[ClaimSignal], output_root: str | Path, construct_context: ConstructContext) -> Result[dict[str, Any]]:
    try:
        allocator = DopaClosureV2Allocator(config_path)
    except ValueError as exc:
        return Err(str(exc))

    run_id = _run_id()
    output = Path(output_root) / "runs" / run_id
    output.mkdir(parents=True, exist_ok=True)
    verdict = validate_construct_context(construct_context)
    write_json(output / "construct_gate.json", asdict(verdict))
    (output / "config.sha256").write_text(allocator.config_hash + "\n", encoding="utf-8")
    (output / "config.yaml").write_text(Path(config_path).read_text(encoding="utf-8"), encoding="utf-8")
    if not verdict.admissible:
        final = {"run_id": run_id, "final_verdict": verdict.verdict, "failure_reasons": verdict.reasons, "config_hash": allocator.config_hash, "commit_sha": _git_head_sha(), "routes": []}
        write_json(output / "final_verdict.json", final)
        return Ok(final)

    cfg = allocator.config
    t = cfg["priority_gate"]["thresholds"]
    costs = cfg["budget"]["action_costs"]
    ledger = BudgetLedger.create(float(cfg["budget"]["envelope"]), float(cfg["budget"].get("probe_tax", 0.0)))
    routes, priorities, artifact_hashes = [], [], {}
    deferred_due_budget = 0

    for claim in claims:
        budget_ratio = 0.0 if float(ledger.envelope) <= 0 else float(ledger.remaining / ledger.envelope)
        priority = allocator.priority_of_verification(claim, budget_ratio=budget_ratio)
        priorities.append(priority)

        desired_mode: RouteMode = (
            RouteMode.REJECT if claim.evidence_risk >= t["reject_evidence_risk"] else
            RouteMode.ESCALATE if priority >= t["escalate"] else
            RouteMode.VERIFY if priority >= t["verify"] else
            RouteMode.CHEAP_TRIAGE if priority >= t["triage"] else
            RouteMode.QUARANTINE
        )
        executed_mode = desired_mode
        unmet_verification_need = False
        quarantine_reason = None

        requested = float(costs[desired_mode.value])
        needs_budgeted_verification = desired_mode in (RouteMode.ESCALATE, RouteMode.VERIFY)
        verify_unaffordable = needs_budgeted_verification and (requested + float(ledger.probe_tax) > float(ledger.remaining))
        if verify_unaffordable:
            unmet_verification_need = True
            deferred_due_budget += 1
            quarantine_reason = "INSUFFICIENT_BUDGET_FOR_VERIFICATION"
            triage_cost = float(costs[RouteMode.CHEAP_TRIAGE.value]) + float(ledger.probe_tax)
            executed_mode = RouteMode.CHEAP_TRIAGE if triage_cost <= float(ledger.remaining) else RouteMode.QUARANTINE

        step = ledger.apply(float(costs[executed_mode.value]), float(costs[RouteMode.QUARANTINE.value]))
        verification_result = "not_run"
        default_status = {
            RouteMode.REJECT: FinalStatus.REJECTED,
            RouteMode.ESCALATE: FinalStatus.ESCALATE,
            RouteMode.VERIFY: FinalStatus.VERIFY,
            RouteMode.CHEAP_TRIAGE: FinalStatus.CHEAP_TRIAGE,
            RouteMode.QUARANTINE: FinalStatus.QUARANTINED,
        }
        final_status = default_status[executed_mode]

        if step.overspend:
            executed_mode, final_status, quarantine_reason = RouteMode.QUARANTINE, FinalStatus.QUARANTINED, "INSUFFICIENT_BUDGET"
        elif verify_unaffordable:
            if executed_mode == RouteMode.CHEAP_TRIAGE:
                final_status = FinalStatus.CHEAP_TRIAGE
            else:
                final_status = FinalStatus.QUARANTINED
        elif executed_mode == RouteMode.VERIFY:
            verification_result = "pass" if claim.evidence_risk <= t["close_evidence_risk_max"] else "inconclusive"
            final_status = FinalStatus.CLOSED if verification_result == "pass" else FinalStatus.QUARANTINED

        claim_dir = output / "claims" / claim.claim_id
        artifact = claim_artifact_name(executed_mode.value, final_status.value)
        route_doc = {
            "claim_id": claim.claim_id,
            "desired_route_mode": desired_mode.value,
            "route_mode": executed_mode.value,
            "epistemic_status": claim.epistemic_status,
            "final_status": final_status.value,
            "priority_of_verification": priority,
            "verification_result": verification_result,
            "quarantine_reason": quarantine_reason,
            "unmet_verification_need": unmet_verification_need,
            "budget": asdict(step),
            "config_hash": allocator.config_hash,
        }
        write_json(claim_dir / artifact, route_doc)
        route_doc["verification_artifact_hash"] = sha256_file(claim_dir / artifact) if final_status == FinalStatus.CLOSED else None
        write_json(claim_dir / "route.json", route_doc)
        artifact_hashes[f"{claim.claim_id}/{artifact}"] = sha256_file(claim_dir / artifact)
        routes.append(route_doc)

    controls_doc = asdict(run_controls(claims, priorities, seed=int(cfg["negative_controls"]["random_routing_seed"])))
    write_json(output / "controls.json", controls_doc)
    final_verdict = "ADMISSIBLE" if controls_doc["passed"] else "INADMISSIBLE"
    result = {
        "run_id": run_id,
        "commit_sha": _git_head_sha(),
        "final_verdict": final_verdict,
        "failure_reasons": [] if final_verdict == "ADMISSIBLE" else ["controls_failed"],
        "config_hash": allocator.config_hash,
        "construct_gate": asdict(verdict),
        "controls": controls_doc,
        "budget_ledger": ledger.snapshot(),
        "deferred_due_budget": deferred_due_budget,
        "routes": routes,
        "artifact_hashes": artifact_hashes,
        "provenance": {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "config_path": str(config_path)},
    }
    write_json(output / "budget_ledger.json", result["budget_ledger"])
    write_json(output / "final_verdict.json", result)
    return Ok(result)
