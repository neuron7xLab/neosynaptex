"""Evidence and status ceiling resolution for semantic drift enforcement."""

from __future__ import annotations

from collections.abc import Mapping

from contracts.claim_strength import STATUS_CEILINGS

_REQUIRED_FIELDS = (
    "substrate",
    "signal",
    "method",
    "window",
    "controls",
    "fake_alternative",
    "falsifier",
    "interpretation_boundary",
)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered not in {"", "0", "false", "none", "null", "no", "missing"}
    return bool(value)


def _complete_contract(evidence: Mapping[str, object]) -> bool:
    return all(_truthy(evidence.get(field)) for field in _REQUIRED_FIELDS)


def ceiling_from_evidence_object(evidence: Mapping[str, object]) -> int:
    status = str(evidence.get("status", "")).strip().lower()
    if not evidence:
        return 0
    if not _complete_contract(evidence):
        return 1

    if (
        _truthy(evidence.get("generalization_authorized"))
        and _truthy(evidence.get("external_replication"))
        and _truthy(evidence.get("multi_substrate"))
    ):
        return 8

    # Analytical theorem layer (Claim C-001 of docs/CLAIM_BOUNDARY.md).
    # A fully specified analytical proof authorises tier-8 language
    # *within the model/graph family covered by the proof*, even when
    # the proof is single-substrate by design (e.g. Kuramoto dense).
    # The interpretation_boundary field in _REQUIRED_FIELDS keeps the
    # scope explicit so language cannot leak outside the proved regime.
    if status == "proved":
        return 8

    if status == "causal" or _truthy(evidence.get("intervention")):
        return 7

    if status == "validated" or (
        _truthy(evidence.get("replication")) and _truthy(evidence.get("gate_closed"))
    ):
        return 6

    if status in {"measured_but_bounded", "bounded_positive"} and (
        _truthy(evidence.get("null_separation"))
        or _truthy(evidence.get("null_hierarchy"))
        or _truthy(evidence.get("survives_null_hierarchy"))
    ):
        return 5

    if status in {"measured", "derived", "enforced"}:
        if not _truthy(evidence.get("controls")):
            return 3
        return 4

    if status in {"draft", "active", "hypothesized"}:
        return 1

    return 0


def resolve_evidence_ceiling(
    linked_evidence_ids: tuple[str, ...], evidence_registry: Mapping[str, Mapping[str, object]]
) -> int:
    if not linked_evidence_ids:
        return 0
    ceilings = [
        ceiling_from_evidence_object(evidence_registry.get(evidence_id, {}))
        for evidence_id in linked_evidence_ids
    ]
    return max(ceilings, default=0)


def resolve_status_ceiling(status: str) -> int:
    return STATUS_CEILINGS.get(status.strip().lower(), 0)


def resolve_authorized_ceiling(
    linked_evidence_ids: tuple[str, ...],
    evidence_registry: Mapping[str, Mapping[str, object]],
    status: str,
) -> int:
    evidence_ceiling = resolve_evidence_ceiling(linked_evidence_ids, evidence_registry)
    status_ceiling = resolve_status_ceiling(status)
    return min(evidence_ceiling, status_ceiling)
