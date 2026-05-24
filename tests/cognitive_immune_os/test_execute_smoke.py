from __future__ import annotations

from cognitive_immune_os.conflict_object import ConflictObject, ConflictSeverity, ConflictType
from cognitive_immune_os.conflict_resolver import ResolutionAction
from cognitive_immune_os.immune_executor import execute_conflict
from cognitive_immune_os.state_model import StateStatus, VerifiedState


def test_execute_conflict_changes_state_from_supplied_policy() -> None:
    states = {"s0": VerifiedState("s0", StateStatus.ACTIVE)}
    policy = {ConflictType.STALE_EVIDENCE.value: (ResolutionAction.STATE_RECHECK,)}
    conflict = ConflictObject(
        conflict_id="c0",
        conflict_type=ConflictType.STALE_EVIDENCE,
        severity=ConflictSeverity.P5,
        targets=("s0",),
        evidence_refs=("evidence/e0.json",),
        rationale="bounded case",
    )
    next_states, changes = execute_conflict(conflict, states, policy=policy)
    assert next_states["s0"].status is StateStatus.RECHECK_REQUIRED
    assert changes[0].after is StateStatus.RECHECK_REQUIRED
