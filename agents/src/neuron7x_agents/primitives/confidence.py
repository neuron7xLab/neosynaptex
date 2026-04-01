"""
Confidence calibration with hard epistemic gates.

The 0.95+ gate is not a suggestion — it is a construction constraint.
No claim may reach 0.95+ without passing ALL three conditions:
    (a) formal proof OR reproducible evidence OR multiple independent sources
    (b) reductio completed — negation leads to contradiction
    (c) zero unrebutted objections remain

If any gate fails → forced downgrade to 0.80-0.94.

This prevents the single most common failure mode in AI systems:
confidence inflation through fluency.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class ConfidenceLevel(enum.Enum):
    """Epistemic confidence tiers with semantic meaning."""

    UNKNOWN = "unknown"  # < 0.40 — say "I don't know"
    UNCERTAIN = "uncertain"  # 0.40-0.59 — show 2-3 variants
    REASONABLE = "reasonable"  # 0.60-0.79 — name alternatives
    STRONG = "strong"  # 0.80-0.94 — evidence + reductio desirable
    PROVEN = "proven"  # 0.95+ — requires proof gate

    @classmethod
    def from_score(cls, score: float) -> ConfidenceLevel:
        """Map a numeric score to its confidence level."""
        if score < 0.40:
            return cls.UNKNOWN
        if score < 0.60:
            return cls.UNCERTAIN
        if score < 0.80:
            return cls.REASONABLE
        if score < 0.95:
            return cls.STRONG
        return cls.PROVEN


@dataclass(frozen=True)
class ProofGate:
    """Gate conditions required for 0.95+ confidence."""

    has_formal_proof: bool = False
    has_reproducible_evidence: bool = False
    has_multiple_independent_sources: bool = False
    reductio_completed: bool = False
    unrebutted_objections: int = 0

    @property
    def evidence_satisfied(self) -> bool:
        """At least one evidence condition met."""
        return (
            self.has_formal_proof
            or self.has_reproducible_evidence
            or self.has_multiple_independent_sources
        )

    @property
    def passed(self) -> bool:
        """All three gate conditions satisfied."""
        return (
            self.evidence_satisfied and self.reductio_completed and self.unrebutted_objections == 0
        )


@dataclass(frozen=True)
class CalibratedConfidence:
    """A confidence value that has passed through calibration gates."""

    raw_score: float
    calibrated_score: float
    level: ConfidenceLevel
    gate: ProofGate | None
    was_downgraded: bool

    @property
    def is_trustworthy(self) -> bool:
        """True if the calibrated score is self-consistent."""
        return self.level == ConfidenceLevel.from_score(self.calibrated_score)


def enforce_gate(score: float, gate: ProofGate | None = None) -> CalibratedConfidence:
    """
    Apply epistemic gate enforcement to a confidence score.

    If score >= 0.95 but the proof gate is not satisfied,
    the score is forcibly downgraded to 0.94.

    Parameters
    ----------
    score : float
        Raw confidence score (0.0-1.0).
    gate : ProofGate, optional
        Proof gate for 0.95+ claims. Required if score >= 0.95.

    Returns
    -------
    CalibratedConfidence
        The gate-enforced confidence with metadata.

    Examples
    --------
    >>> enforce_gate(0.97, ProofGate(has_formal_proof=True, reductio_completed=True))
    CalibratedConfidence(raw_score=0.97, calibrated_score=0.97, ...)

    >>> enforce_gate(0.97)  # no gate → forced downgrade
    CalibratedConfidence(raw_score=0.97, calibrated_score=0.94, was_downgraded=True)
    """
    score = max(0.0, min(1.0, score))
    downgraded = False

    if score >= 0.95:
        if gate is None or not gate.passed:
            score_out = 0.94
            downgraded = True
        else:
            score_out = score
    else:
        score_out = score

    return CalibratedConfidence(
        raw_score=score,
        calibrated_score=score_out,
        level=ConfidenceLevel.from_score(score_out),
        gate=gate,
        was_downgraded=downgraded,
    )


def calibrate(
    score: float,
    *,
    fragility_check: str | None = None,
) -> CalibratedConfidence:
    """
    Calibrate a confidence score with optional fragility analysis.

    The fragility check asks: "What ONE new piece of evidence could
    drop my confidence by 0.2+?" If the answer is easy to imagine,
    the score is likely overcalibrated.

    Parameters
    ----------
    score : float
        Raw confidence score (0.0-1.0).
    fragility_check : str, optional
        Description of what could drop confidence by 0.2+.
        If provided and non-empty, score is reduced by 0.05 as
        a humility correction.

    Returns
    -------
    CalibratedConfidence
        Calibrated confidence with level classification.
    """
    adjusted = max(0.0, min(1.0, score))

    if fragility_check and len(fragility_check.strip()) > 0:
        adjusted = max(0.0, adjusted - 0.05)

    return enforce_gate(adjusted)
