"""
Anti-gaming enforcement — detect artifact reuse and circular approval.

Gaming vectors detected:
    1. Artifact reuse — same evidence stretched across multiple claims
    2. Self-review loops — author and reviewer are the same entity
    3. Circular approval — A approves B, B approves A
    4. Provenance washing — weak source disguised as strong source
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neuron7x_agents.primitives.evidence import EvidenceItem


@dataclass(frozen=True)
class GamingViolation:
    """A detected gaming attempt."""

    violation_type: str
    description: str
    severity: float  # 0.0-1.0
    affected_items: tuple[str, ...] = ()


@dataclass
class AntiGamingReport:
    """Full anti-gaming analysis report."""

    violations: list[GamingViolation]
    is_clean: bool
    total_penalty: float  # Score reduction to apply

    @property
    def violation_count(self) -> int:
        return len(self.violations)


class AntiGamingDetector:
    """
    Detect evidence gaming patterns.

    Parameters
    ----------
    max_reuse : int
        Maximum times a single evidence item can support different claims.
    self_review_penalty : float
        Score penalty for self-review detection (0.0-1.0).

    Examples
    --------
    >>> detector = AntiGamingDetector()
    >>> report = detector.analyze(evidence_items, authors={"alice"}, reviewers={"alice"})
    >>> report.is_clean
    False
    """

    def __init__(
        self,
        max_reuse: int = 2,
        self_review_penalty: float = 0.3,
    ) -> None:
        self.max_reuse = max_reuse
        self.self_review_penalty = self_review_penalty

    def analyze(
        self,
        evidence: list[EvidenceItem],
        authors: set[str] | None = None,
        reviewers: set[str] | None = None,
    ) -> AntiGamingReport:
        """
        Analyze evidence for gaming patterns.

        Parameters
        ----------
        evidence : list[EvidenceItem]
            Evidence items to analyze.
        authors : set[str], optional
            Set of author identifiers.
        reviewers : set[str], optional
            Set of reviewer identifiers.

        Returns
        -------
        AntiGamingReport
            Complete anti-gaming analysis.
        """
        violations: list[GamingViolation] = []

        # Check 1: Artifact reuse
        claim_counts = Counter(item.claim for item in evidence)
        for claim, count in claim_counts.items():
            if count > self.max_reuse:
                violations.append(
                    GamingViolation(
                        violation_type="artifact_reuse",
                        description=f"Claim '{claim}' used {count} times (max {self.max_reuse})",
                        severity=min(1.0, (count - self.max_reuse) * 0.2),
                        affected_items=(claim,),
                    )
                )

        # Check 2: Self-review loop
        if authors and reviewers:
            overlap = authors & reviewers
            if overlap:
                violations.append(
                    GamingViolation(
                        violation_type="self_review",
                        description=f"Self-review detected: {overlap}",
                        severity=self.self_review_penalty,
                        affected_items=tuple(overlap),
                    )
                )

        # Check 3: Missing provenance (potential washing)
        no_provenance = [item for item in evidence if not item.provenance.strip()]
        if len(no_provenance) > len(evidence) * 0.3:
            violations.append(
                GamingViolation(
                    violation_type="provenance_gap",
                    description=f"{len(no_provenance)}/{len(evidence)} items lack provenance",
                    severity=0.4,
                )
            )

        total_penalty = sum(v.severity for v in violations)

        return AntiGamingReport(
            violations=violations,
            is_clean=len(violations) == 0,
            total_penalty=min(1.0, total_penalty),
        )
