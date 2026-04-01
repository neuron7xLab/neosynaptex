"""
Evidence primitives — Markov blanket epistemic tiering.

Every claim is classified as one of three tiers:
    GIVEN       — directly observed, verifiable fact
    INFERRED    — derived from given evidence via valid reasoning
    SPECULATED  — hypothesis, not yet validated

The tiers are never mixed. Mixing tiers is the primary mechanism
by which AI systems produce convincing but unfounded claims.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class EvidenceTier(enum.Enum):
    """Epistemic tier — the provenance of a claim."""

    GIVEN = "given"  # Directly observed or verifiable
    INFERRED = "inferred"  # Derived from given evidence
    SPECULATED = "speculated"  # Hypothesis, not validated

    @property
    def weight(self) -> float:
        """Precision weight for this tier."""
        weights = {
            EvidenceTier.GIVEN: 1.0,
            EvidenceTier.INFERRED: 0.6,
            EvidenceTier.SPECULATED: 0.2,
        }
        return weights[self]


class EvidenceSource(enum.Enum):
    """Source reliability hierarchy (precision weighting)."""

    FORMAL_PROOF = "formal_proof"
    EXPERIMENT = "experiment"
    PEER_REVIEWED = "peer_reviewed"
    EXPERT_OPINION = "expert_opinion"
    ANECDOTAL = "anecdotal"
    SELF_ATTESTED = "self_attested"

    @property
    def reliability(self) -> float:
        """Reliability score (0.0-1.0)."""
        scores = {
            EvidenceSource.FORMAL_PROOF: 1.0,
            EvidenceSource.EXPERIMENT: 0.9,
            EvidenceSource.PEER_REVIEWED: 0.8,
            EvidenceSource.EXPERT_OPINION: 0.6,
            EvidenceSource.ANECDOTAL: 0.3,
            EvidenceSource.SELF_ATTESTED: 0.1,
        }
        return scores[self]


@dataclass(frozen=True)
class EvidenceItem:
    """
    A single piece of evidence with full provenance.

    Parameters
    ----------
    claim : str
        The factual claim this evidence supports.
    tier : EvidenceTier
        Epistemic tier (given/inferred/speculated).
    source : EvidenceSource
        Source type for precision weighting.
    content : Any
        The actual evidence content.
    provenance : str
        Where this evidence came from (URL, DOI, file path, etc.).
    """

    claim: str
    tier: EvidenceTier
    source: EvidenceSource
    content: Any = None
    provenance: str = ""

    @property
    def precision_weight(self) -> float:
        """Combined precision weight: tier × source reliability."""
        return self.tier.weight * self.source.reliability


@dataclass
class MarkovBlanket:
    """
    Epistemic boundary — separates known from unknown.

    The Markov blanket maintains three partitions of claims,
    ensuring no mixing of epistemic tiers.

    Examples
    --------
    >>> blanket = MarkovBlanket()
    >>> blanket.add_given(EvidenceItem("sky is blue", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT))
    >>> item = EvidenceItem("scatters light", EvidenceTier.INFERRED, EvidenceSource.PEER_REVIEWED)
    >>> blanket.add_inferred(item)
    >>> blanket.total_evidence
    2
    """

    given: list[EvidenceItem] = field(default_factory=list)
    inferred: list[EvidenceItem] = field(default_factory=list)
    speculated: list[EvidenceItem] = field(default_factory=list)

    def add_given(self, item: EvidenceItem) -> None:
        """Add a directly observed fact."""
        if item.tier != EvidenceTier.GIVEN:
            msg = f"Expected GIVEN tier, got {item.tier}"
            raise ValueError(msg)
        self.given.append(item)

    def add_inferred(self, item: EvidenceItem) -> None:
        """Add an inferred claim."""
        if item.tier != EvidenceTier.INFERRED:
            msg = f"Expected INFERRED tier, got {item.tier}"
            raise ValueError(msg)
        self.inferred.append(item)

    def add_speculated(self, item: EvidenceItem) -> None:
        """Add a speculative hypothesis."""
        if item.tier != EvidenceTier.SPECULATED:
            msg = f"Expected SPECULATED tier, got {item.tier}"
            raise ValueError(msg)
        self.speculated.append(item)

    @property
    def total_evidence(self) -> int:
        """Total number of evidence items across all tiers."""
        return len(self.given) + len(self.inferred) + len(self.speculated)

    @property
    def aggregate_precision(self) -> float:
        """Weighted average precision across all evidence."""
        all_items = self.given + self.inferred + self.speculated
        if not all_items:
            return 0.0
        return sum(i.precision_weight for i in all_items) / len(all_items)

    def summary(self) -> dict[str, int]:
        """Return tier counts."""
        return {
            "given": len(self.given),
            "inferred": len(self.inferred),
            "speculated": len(self.speculated),
        }
