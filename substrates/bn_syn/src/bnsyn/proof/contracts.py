"""Canonical proof mode contracts and helpers."""

from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
from typing import Any

CANONICAL_BASE_CONTRACT = "canonical-base"
CANONICAL_EXPORT_PROOF_CONTRACT = "canonical-export-proof"

CANONICAL_BASE_COMMAND = "bnsyn run --profile canonical --plot"
CANONICAL_EXPORT_PROOF_COMMAND = "bnsyn run --profile canonical --plot --export-proof"

BASE_ARTIFACTS: tuple[str, ...] = (
    "emergence_plot.png",
    "summary_metrics.json",
    "criticality_report.json",
    "avalanche_report.json",
    "phase_space_report.json",
    "population_rate_trace.npy",
    "sigma_trace.npy",
    "coherence_trace.npy",
    "phase_space_rate_sigma.png",
    "phase_space_rate_coherence.png",
    "phase_space_activity_map.png",
    "avalanche_fit_report.json",
    "robustness_report.json",
    "envelope_report.json",
    "run_manifest.json",
)
EXPORT_PROOF_ARTIFACTS: tuple[str, ...] = BASE_ARTIFACTS + ("proof_report.json",)

EMERGENCE_ARTIFACTS: tuple[str, ...] = EXPORT_PROOF_ARTIFACTS + (
    "emergence_proof_report.json",
    "causality_report.json",
    "phi_proxy_report.json",
    "assembly_report.json",
    "structural_plasticity_report.json",
    "renormalization_report.json",
    "neuromodulation_report.json",
)


@dataclass(frozen=True)
class ManifestMode:
    bundle_contract: str
    export_proof: bool
    cmd: str


def command_for_export_proof(export_proof: bool) -> str:
    return CANONICAL_EXPORT_PROOF_COMMAND if export_proof else CANONICAL_BASE_COMMAND


def bundle_contract_for_export_proof(export_proof: bool) -> str:
    return CANONICAL_EXPORT_PROOF_CONTRACT if export_proof else CANONICAL_BASE_CONTRACT


def artifacts_for_export_proof(export_proof: bool) -> tuple[str, ...]:
    return EXPORT_PROOF_ARTIFACTS if export_proof else BASE_ARTIFACTS


def mode_from_manifest(manifest: dict[str, Any]) -> tuple[ManifestMode | None, list[str]]:
    errors: list[str] = []

    cmd_raw = manifest.get("cmd")
    contract_raw = manifest.get("bundle_contract")
    export_raw = manifest.get("export_proof")
    artifacts_raw = manifest.get("artifacts")

    cmd: str | None = cmd_raw if isinstance(cmd_raw, str) else None
    bundle_contract: str | None = contract_raw if isinstance(contract_raw, str) else None
    export_proof: bool | None = export_raw if isinstance(export_raw, bool) else None
    artifacts: dict[str, Any] | None = artifacts_raw if isinstance(artifacts_raw, dict) else None

    if cmd is None:
        errors.append("manifest cmd must be string")
    if bundle_contract not in {CANONICAL_BASE_CONTRACT, CANONICAL_EXPORT_PROOF_CONTRACT}:
        errors.append("manifest bundle_contract invalid")
    if export_proof is None:
        errors.append("manifest export_proof must be boolean")
    if artifacts is None:
        errors.append("manifest artifacts must be object")

    if errors:
        return None, errors

    assert artifacts is not None
    assert cmd is not None
    assert bundle_contract is not None
    assert export_proof is not None

    has_proof_entry = "proof_report.json" in artifacts

    if export_proof:
        if cmd != CANONICAL_EXPORT_PROOF_COMMAND:
            errors.append("export-proof mode requires export-proof cmd")
        if bundle_contract != CANONICAL_EXPORT_PROOF_CONTRACT:
            errors.append("export-proof mode requires canonical-export-proof bundle_contract")
        if not has_proof_entry:
            errors.append("export-proof mode requires proof_report.json manifest entry")
    else:
        if cmd != CANONICAL_BASE_COMMAND:
            errors.append("base mode requires base cmd")
        if bundle_contract != CANONICAL_BASE_CONTRACT:
            errors.append("base mode requires canonical-base bundle_contract")
        if has_proof_entry:
            errors.append("base mode forbids proof_report.json manifest entry")

    if errors:
        return None, errors

    return ManifestMode(bundle_contract=bundle_contract, export_proof=export_proof, cmd=cmd), []


MANIFEST_SELF_HASH_PLACEHOLDER = "__RUN_MANIFEST_SELF_HASH__"


def manifest_self_hash(manifest: dict[str, Any]) -> str:
    """Compute deterministic self-hash for run_manifest.json.

    The run_manifest.json artifact entry is normalized to a fixed placeholder before
    hashing to break recursive self-reference while keeping deterministic integrity.
    """
    payload = copy.deepcopy(manifest)
    artifacts_raw = payload.get("artifacts")
    artifacts: dict[str, Any] = dict(artifacts_raw) if isinstance(artifacts_raw, dict) else {}
    artifacts["run_manifest.json"] = MANIFEST_SELF_HASH_PLACEHOLDER
    payload["artifacts"] = artifacts
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
