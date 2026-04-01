"""
Epistemic Gate — fail-closed verification for claims and evidence.

Design principle: missing evidence is a constraint, not a gap to fill.

    Fail-OPEN  system: missing evidence → evaluator fills with judgment
    Fail-CLOSED system: missing evidence → score is capped, gate blocks

This gate treats artifact content as DATA, not authority.
The protocol holds authority. The evidence is scored, not obeyed.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neuron7x_agents.primitives.evidence import EvidenceItem


class GateStatus(enum.Enum):
    """Gate evaluation outcome."""

    PASSED = "passed"
    CAPPED = "capped"  # Evidence insufficient → score capped
    BLOCKED = "blocked"  # Integrity violation → gate blocked
    INVALID = "invalid"  # Schema/structure failure → inadmissible


@dataclass(frozen=True)
class GateVerdict:
    """Complete gate evaluation result."""

    status: GateStatus
    score: float  # 0.0-1.0, after caps
    max_possible_score: float  # Cap imposed by evidence quality
    evidence_count: int
    tier_distribution: dict[str, int]
    violations: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_admissible(self) -> bool:
        """True if the evaluation passed or was capped (not blocked/invalid)."""
        return self.status in (GateStatus.PASSED, GateStatus.CAPPED)


class EpistemicGate:
    """
    Fail-closed epistemic verification gate.

    Evidence is evaluated against three conditions:
        1. Sufficiency — enough evidence to support the claim?
        2. Independence — no circular approval loops?
        3. Provenance — traceable origin for every item?

    If any condition fails, the score is capped or blocked.

    Parameters
    ----------
    min_evidence : int
        Minimum number of evidence items required.
    min_given_ratio : float
        Minimum ratio of GIVEN-tier evidence (0.0-1.0).
    require_provenance : bool
        Whether provenance is required for all items.

    Examples
    --------
    >>> gate = EpistemicGate()
    >>> evidence = [
    ...     EvidenceItem("claim A", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:10.1234"),
    ...     EvidenceItem("claim B", EvidenceTier.INFERRED, EvidenceSource.PEER_REVIEWED, provenance="arxiv:2026.001"),
    ... ]
    >>> verdict = gate.evaluate(evidence)
    >>> verdict.is_admissible
    True
    """

    def __init__(
        self,
        min_evidence: int = 2,
        min_given_ratio: float = 0.3,
        require_provenance: bool = True,
    ) -> None:
        self.min_evidence = min_evidence
        self.min_given_ratio = min_given_ratio
        self.require_provenance = require_provenance

    def evaluate(
        self,
        evidence: list[EvidenceItem],
        claimed_score: float = 1.0,
    ) -> GateVerdict:
        """
        Evaluate evidence through the fail-closed gate.

        Parameters
        ----------
        evidence : list[EvidenceItem]
            Evidence items to evaluate.
        claimed_score : float
            The score claimed by the evaluand (will be capped if needed).

        Returns
        -------
        GateVerdict
            Complete gate evaluation with status and capped score.
        """
        violations: list[str] = []

        # Check: sufficiency
        if len(evidence) < self.min_evidence:
            violations.append(
                f"Insufficient evidence: {len(evidence)} < {self.min_evidence} required"
            )

        # Check: tier distribution
        tier_counts = {"given": 0, "inferred": 0, "speculated": 0}
        for item in evidence:
            tier_counts[item.tier.value] += 1

        total = len(evidence) or 1
        given_ratio = tier_counts["given"] / total
        if given_ratio < self.min_given_ratio:
            violations.append(
                f"Given-tier evidence ratio too low: {given_ratio:.2f} < {self.min_given_ratio}"
            )

        # Check: provenance
        if self.require_provenance:
            missing_provenance = [item for item in evidence if not item.provenance.strip()]
            if missing_provenance:
                violations.append(f"{len(missing_provenance)} items missing provenance")

        # Compute cap based on evidence quality
        avg_precision = (
            sum(item.precision_weight for item in evidence) / total if evidence else 0.0
        )
        max_score = min(1.0, avg_precision * 1.2)  # Slight headroom

        # Determine status
        if not evidence:
            status = GateStatus.INVALID
            final_score = 0.0
            max_score = 0.0
        elif any("Insufficient" in v for v in violations):
            status = GateStatus.BLOCKED
            final_score = 0.0
        elif violations:
            status = GateStatus.CAPPED
            final_score = min(claimed_score, max_score * 0.8)
        else:
            status = GateStatus.PASSED
            final_score = min(claimed_score, max_score)

        return GateVerdict(
            status=status,
            score=final_score,
            max_possible_score=max_score,
            evidence_count=len(evidence),
            tier_distribution=tier_counts,
            violations=tuple(violations),
            metadata={"avg_precision": avg_precision},
        )
