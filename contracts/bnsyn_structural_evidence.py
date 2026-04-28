"""BN-Syn local structural evidence — typed boundary contract.

Imports BN-Syn canonical proof bundle outputs as a strictly-typed
*structural-evidence-only* witness for NeoSynaptex. This contract does
NOT speak about γ, NOT about consciousness, NOT about cross-substrate
universality. It only carries the three local structural metric
families that BN-Syn actually emits:

1. Branching-ratio surrogate κ (= ``criticality_report.sigma_mean``).
2. Avalanche distribution + power-law fit quality
   (``avalanche_report.json`` + ``avalanche_fit_report.json``).
3. Phase coherence summary (``phase_space_report.coherence_mean``).

Plus determinism/provenance lifted from ``run_manifest.json`` and
``robustness_report.replay_check``.

Note on naming: BN-Syn does NOT emit an explicit phase-randomized
surrogate-rejection flag for the coherence trace. The closest proxy is
the power-law fit verdict on the avalanche distribution
(``avalanche_fit_report.validity.verdict == "PASS"`` AND
``p_value >= p_value_min``). We surface this as
``phase_surrogate_rejected`` only when callers explicitly map it; if the
caller cannot honestly justify the mapping, the field stays
``False`` and the verdict downgrades to ``ARTIFACT_SUSPECTED``.

Verdict surface (``BnSynEvidenceVerdict``):

* ``NO_ADMISSIBLE_CLAIM`` — any required metric missing/NaN/inf.
* ``ARTIFACT_SUSPECTED`` — surrogate not rejected.
* ``LOCAL_STRUCTURAL_EVIDENCE_ONLY`` — best honest case. NEVER
  upgraded to "validated" here; that requires NeoSynaptex's own
  null-control + provenance + determinism gates downstream.
* ``VALIDATED_SUBSTRATE_EVIDENCE`` — only emitted when both local pass
  AND a γ-side pass is supplied by the caller (this contract refuses
  to estimate γ from structural metrics; see
  ``substrates/bnsyn_structural_adapter.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "BnSynStructuralMetrics",
    "BnSynEvidenceVerdict",
    "LocalStructuralStatus",
    "GammaStatus",
    "ArtifactStatus",
    "ClaimStatusLabel",
    "validate_metrics",
]


# Verdict-component label vocabularies. Plain string constants rather
# than Enums to keep the contract trivially serialisable into the
# importer's JSON output without a custom encoder.

LocalStructuralStatus: Final[tuple[str, ...]] = (
    "PASS",
    "FAIL",
    "MISSING",
)

GammaStatus: Final[tuple[str, ...]] = (
    "NO_ADMISSIBLE_CLAIM",
    "PASS",
    "FAIL",
    "MISSING",
)

ArtifactStatus: Final[tuple[str, ...]] = (
    "NOT_SUSPECTED",
    "ARTIFACT_SUSPECTED",
    "MISSING",
)

ClaimStatusLabel: Final[tuple[str, ...]] = (
    "NO_ADMISSIBLE_CLAIM",
    "ARTIFACT_SUSPECTED",
    "LOCAL_STRUCTURAL_EVIDENCE_ONLY",
    "VALIDATED_SUBSTRATE_EVIDENCE",
)


@dataclass(frozen=True, slots=True)
class BnSynStructuralMetrics:
    """Strictly-typed BN-Syn local structural metrics.

    All numeric fields must be finite floats (or, where annotated,
    ``None``). Validation is performed by ``validate_metrics``. The
    dataclass itself is a passive carrier: it does NOT enforce
    finiteness in ``__post_init__`` because the importer needs to be
    able to instantiate the object first and *then* run the validator
    so that the failure reason can be reported in the verdict.

    Fields
    ------
    kappa
        Branching-ratio surrogate. BN-Syn maps this onto
        ``criticality_report.sigma_mean``. At criticality the network
        targets ``kappa ≈ 1.0``.
    kappa_ci_low, kappa_ci_high
        Confidence-interval bounds on κ if the source bundle reports
        them. BN-Syn does not currently emit a CI, so these are
        normally ``None``; the verdict logic accepts either a tight
        point estimate near 1.0 *or* a CI containing 1.0.
    avalanche_fit_quality
        Goodness-of-fit p-value (or KS-distance-derived score) for the
        power-law avalanche-size distribution. Convention: higher is
        better; the threshold is configured externally.
    avalanche_distribution_summary
        Free-form summary dict. Required keys: ``alpha`` (size
        exponent), ``avalanche_count``, ``size_max``. The presence of
        this dict is what gates "avalanche distribution exists".
    phase_coherence
        Mean phase coherence ``\\in [0, 1]``. BN-Syn maps this onto
        ``phase_space_report.coherence_mean``.
    phase_surrogate_rejected
        Whether a phase-randomized null was rejected for the coherence
        trace. BN-Syn does NOT directly emit this; the importer can
        only set it to True when the caller supplies an explicit
        proxy mapping (typically: avalanche power-law-fit verdict =
        PASS and p_value >= configured floor). When the caller cannot
        honestly justify the mapping, this field is False and the
        verdict downgrades to ARTIFACT_SUSPECTED.
    """

    kappa: float
    kappa_ci_low: float | None
    kappa_ci_high: float | None
    avalanche_fit_quality: float
    avalanche_distribution_summary: dict[str, Any]
    phase_coherence: float
    phase_surrogate_rejected: bool


@dataclass(frozen=True, slots=True)
class BnSynEvidenceVerdict:
    """Final verdict returned by the importer / adapter.

    Fields
    ------
    local_structural_status
        One of ``LocalStructuralStatus``.
    gamma_status
        One of ``GammaStatus``. For the BN-Syn structural-only path
        this is ``NO_ADMISSIBLE_CLAIM`` by construction (κ alone is
        not γ; we refuse to fabricate C/K from a single point).
    artifact_status
        One of ``ArtifactStatus``.
    claim_status
        One of ``ClaimStatusLabel``. Computed by
        ``BnSynStructuralAdapter.compute_verdict`` — never assigned by
        the importer in isolation.
    reasons
        Tuple of short machine-readable reason codes explaining the
        downgrade path. Append-only, sorted by severity (most-severe
        first). Empty tuple iff status is the best plausible.
    """

    local_structural_status: str
    gamma_status: str
    artifact_status: str
    claim_status: str
    reasons: tuple[str, ...]


def _is_finite_float(value: object) -> bool:
    """Return True iff ``value`` is a finite (non-NaN, non-inf) float/int."""
    if isinstance(value, bool):
        # bool is a subclass of int in Python; reject it as a numeric.
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def validate_metrics(metrics: BnSynStructuralMetrics) -> tuple[str, ...]:
    """Return a tuple of failure-reason codes; empty tuple iff valid.

    The validator is fail-closed: any missing, NaN, or infinite numeric
    field produces a reason code. Optional CI bounds are allowed to be
    None, but if either bound is supplied as a non-None value it must
    be finite.

    Reason codes are short, hyphenated, screaming-snake-case so they
    are stable for downstream pattern-matching:

    * ``KAPPA_NOT_FINITE``
    * ``KAPPA_CI_LOW_NOT_FINITE``
    * ``KAPPA_CI_HIGH_NOT_FINITE``
    * ``AVALANCHE_FIT_QUALITY_NOT_FINITE``
    * ``AVALANCHE_DISTRIBUTION_SUMMARY_EMPTY``
    * ``AVALANCHE_DISTRIBUTION_SUMMARY_NOT_DICT``
    * ``PHASE_COHERENCE_NOT_FINITE``
    * ``PHASE_COHERENCE_OUT_OF_BAND``
    * ``PHASE_SURROGATE_REJECTED_NOT_BOOL``
    """

    reasons: list[str] = []

    if not _is_finite_float(metrics.kappa):
        reasons.append("KAPPA_NOT_FINITE")

    if metrics.kappa_ci_low is not None and not _is_finite_float(metrics.kappa_ci_low):
        reasons.append("KAPPA_CI_LOW_NOT_FINITE")
    if metrics.kappa_ci_high is not None and not _is_finite_float(metrics.kappa_ci_high):
        reasons.append("KAPPA_CI_HIGH_NOT_FINITE")

    if not _is_finite_float(metrics.avalanche_fit_quality):
        reasons.append("AVALANCHE_FIT_QUALITY_NOT_FINITE")

    if not isinstance(metrics.avalanche_distribution_summary, dict):
        reasons.append("AVALANCHE_DISTRIBUTION_SUMMARY_NOT_DICT")
    elif len(metrics.avalanche_distribution_summary) == 0:
        reasons.append("AVALANCHE_DISTRIBUTION_SUMMARY_EMPTY")

    if not _is_finite_float(metrics.phase_coherence):
        reasons.append("PHASE_COHERENCE_NOT_FINITE")
    elif not (0.0 <= float(metrics.phase_coherence) <= 1.0):
        reasons.append("PHASE_COHERENCE_OUT_OF_BAND")

    if not isinstance(metrics.phase_surrogate_rejected, bool):
        reasons.append("PHASE_SURROGATE_REJECTED_NOT_BOOL")

    return tuple(reasons)
