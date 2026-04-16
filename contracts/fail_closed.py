"""Fail-closed verdict contracts.

Defines the canonical verdict enum and aggregation law used by the
Neosynaptex truth engine. The aggregation law is intentionally strict:

* An empty verdict collection never produces VERIFIED.
* Every registered domain must contribute an explicit status; a missing
  or NaN assessment is recorded as MISSING and cannot upgrade the global
  verdict.
* The presence of any FAIL_CLOSED domain demotes the global verdict to
  FAIL_CLOSED.
* VERIFIED is emitted only when every registered domain is explicitly
  VERIFIED.

These rules mirror the "no valid input -> no metric" governing law and
prevent `all([])` from silently evaluating to success.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Verdict",
    "DomainAssessment",
    "aggregate_verdicts",
    "parse_verdict",
]


class Verdict(str, Enum):
    """Canonical verdict states.

    Inherits from ``str`` so existing code that compares against string
    literals (``"VERIFIED"``, ``"FRAGILE"``, ...) keeps working while
    callers that need enum discipline can switch to ``Verdict.VERIFIED``.
    """

    VERIFIED = "VERIFIED"
    CONSTRUCTED = "CONSTRUCTED"
    FRAGILE = "FRAGILE"
    INCONCLUSIVE = "INCONCLUSIVE"
    MISSING = "MISSING"
    FAIL_CLOSED = "FAIL_CLOSED"


_HARD_FAIL: frozenset[Verdict] = frozenset({Verdict.FAIL_CLOSED})
_BLOCKING_UPGRADE: frozenset[Verdict] = frozenset(
    {Verdict.CONSTRUCTED, Verdict.FRAGILE, Verdict.INCONCLUSIVE, Verdict.MISSING}
)


def parse_verdict(label: str | Verdict | None) -> Verdict:
    """Map an arbitrary label onto the canonical Verdict enum.

    ``None`` and unknown labels map to ``MISSING`` rather than silently
    defaulting to a passing state.
    """

    if label is None:
        return Verdict.MISSING
    if isinstance(label, Verdict):
        return label
    text = str(label).strip().upper()
    for member in Verdict:
        if member.value == text:
            return member
    return Verdict.MISSING


@dataclass(frozen=True)
class DomainAssessment:
    """Per-domain epistemic verdict plus evidence trail.

    ``status``            -- verdict for this domain (never None).
    ``blocking_reason``   -- human-readable reason when status != VERIFIED.
    ``evidence_state``    -- structured payload from the assessor.
    """

    domain: str
    status: Verdict
    blocking_reason: str = ""
    evidence_state: Mapping[str, object] = field(default_factory=dict)


def aggregate_verdicts(
    domain_order: list[str] | tuple[str, ...],
    per_domain: Mapping[str, DomainAssessment | Verdict | str | None],
) -> Verdict:
    """Combine per-domain assessments into a single fail-closed verdict.

    Rules (in precedence order):

    1. No registered domains -> INCONCLUSIVE (never VERIFIED).
    2. Any FAIL_CLOSED domain -> FAIL_CLOSED.
    3. Any MISSING domain (or mismatched cardinality) -> FAIL_CLOSED.
       A registered domain that failed to produce a verdict is a hard
       audit defect, not a soft skip.
    4. Any CONSTRUCTED domain -> CONSTRUCTED (tautology poisons global).
    5. Any FRAGILE domain -> FRAGILE.
    6. Any INCONCLUSIVE domain -> INCONCLUSIVE.
    7. All domains VERIFIED -> VERIFIED.
    """

    if not domain_order:
        return Verdict.INCONCLUSIVE

    resolved: list[Verdict] = []
    for name in domain_order:
        entry = per_domain.get(name) if per_domain is not None else None
        if entry is None:
            resolved.append(Verdict.MISSING)
        elif isinstance(entry, DomainAssessment):
            resolved.append(entry.status)
        elif isinstance(entry, Verdict):
            resolved.append(entry)
        else:
            resolved.append(parse_verdict(entry))

    if len(resolved) != len(domain_order):  # pragma: no cover - defensive
        return Verdict.FAIL_CLOSED

    if any(v in _HARD_FAIL for v in resolved):
        return Verdict.FAIL_CLOSED

    if any(v == Verdict.MISSING for v in resolved):
        return Verdict.FAIL_CLOSED

    if any(v == Verdict.CONSTRUCTED for v in resolved):
        return Verdict.CONSTRUCTED

    if any(v == Verdict.FRAGILE for v in resolved):
        return Verdict.FRAGILE

    if any(v == Verdict.INCONCLUSIVE for v in resolved):
        return Verdict.INCONCLUSIVE

    if all(v == Verdict.VERIFIED for v in resolved):
        return Verdict.VERIFIED

    return Verdict.INCONCLUSIVE
