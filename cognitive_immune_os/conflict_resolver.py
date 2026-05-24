from __future__ import annotations

from enum import Enum

from cognitive_immune_os.conflict_object import ConflictObject, ConflictSeverity, ConflictType


class ResolutionAction(str, Enum):
    STATE_DEMOTION = "STATE_DEMOTION"
    STATE_HOLD = "STATE_HOLD"
    STATE_RECHECK = "STATE_RECHECK"
    POLICY_REVISION = "POLICY_REVISION"
    SCOPE_NARROWING = "SCOPE_NARROWING"
    UNTESTED_MARKER = "UNTESTED_MARKER"


_RESOLUTION_TABLE: dict[ConflictType, tuple[ResolutionAction, ...]] = {
    ConflictType.SELF_CONTRADICTION: (ResolutionAction.STATE_DEMOTION, ResolutionAction.STATE_HOLD),
    ConflictType.INVALID_INSTRUMENT: (ResolutionAction.UNTESTED_MARKER, ResolutionAction.STATE_RECHECK),
    ConflictType.PUBLIC_SURFACE_OVERREACH: (ResolutionAction.SCOPE_NARROWING, ResolutionAction.STATE_DEMOTION),
    ConflictType.EXTERNAL_REPLICATION_FAILURE: (ResolutionAction.STATE_RECHECK, ResolutionAction.STATE_DEMOTION),
    ConflictType.POLICY_BIAS: (ResolutionAction.POLICY_REVISION, ResolutionAction.STATE_RECHECK),
    ConflictType.STALE_EVIDENCE: (ResolutionAction.STATE_RECHECK,),
    ConflictType.DOCUMENTATION_AMBIGUITY: (ResolutionAction.SCOPE_NARROWING,),
}


_SEVERITY_RANK: dict[ConflictSeverity, int] = {
    ConflictSeverity.P0: 0,
    ConflictSeverity.P1: 1,
    ConflictSeverity.P2: 2,
    ConflictSeverity.P3: 3,
    ConflictSeverity.P4: 4,
    ConflictSeverity.P5: 5,
    ConflictSeverity.P6: 6,
}


def resolve_conflict(conflict: ConflictObject) -> tuple[ResolutionAction, ...]:
    actions = _RESOLUTION_TABLE[conflict.conflict_type]
    if not actions:
        raise RuntimeError("empty conflict resolution")
    return actions


def priority(conflict: ConflictObject) -> int:
    return _SEVERITY_RANK[conflict.severity]
