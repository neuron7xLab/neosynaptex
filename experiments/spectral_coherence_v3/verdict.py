"""Phase 7 — verdict logic.

Ten gates collapse into SHARED_SPECTRAL_COMPONENT / WEAK_SPECTRAL_OVERLAP
/ SPECTRALLY_INDEPENDENT. A positive verdict requires ALL ten gates to
pass — missing physical match alone caps at WEAK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "VerdictInputs",
    "VerdictReport",
    "assign_verdict",
    "SHARED_COHERENCE_FLOOR",
    "Z_SCORE_FLOOR",
    "EMPIRICAL_P_LIMIT",
    "WEAK_COHERENCE_RANGE",
]


SHARED_COHERENCE_FLOOR = 0.50
Z_SCORE_FLOOR = 3.0
EMPIRICAL_P_LIMIT = 0.01
WEAK_COHERENCE_RANGE = (0.30, 0.50)
WEAK_Z_RANGE = (2.0, 3.0)
INDEP_COHERENCE_CEIL = 0.30
INDEP_Z_CEIL = 2.0
INDEP_P_FLOOR = 0.05
NAN_RATE_LIMIT = 0.05


VerdictLabel = Literal[
    "SHARED_SPECTRAL_COMPONENT",
    "WEAK_SPECTRAL_OVERLAP",
    "SPECTRALLY_INDEPENDENT",
]


@dataclass(frozen=True)
class VerdictInputs:
    physical_frequency_match: bool
    frequency_stable: bool
    max_coherence_welch: float
    max_coherence_multitaper: float
    max_z_score: float
    empirical_p_value: float
    wavelet_persistent_band: bool
    segment_robustness_pass: bool
    repetition_detected: bool
    nan_rate_bnsyn: float
    nan_rate_geosync: float
    estimator_agreement: bool


@dataclass(frozen=True)
class VerdictReport:
    label: VerdictLabel
    reasons: tuple[str, ...]
    positive_gates_passed: tuple[str, ...]
    positive_gates_failed: tuple[str, ...]


def _positive_gates(inp: VerdictInputs) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []

    def _check(name: str, ok: bool) -> None:
        (passed if ok else failed).append(name)

    _check("physical_frequency_match", inp.physical_frequency_match)
    _check("frequency_stable", inp.frequency_stable)
    _check("max_coherence_welch>0.5", inp.max_coherence_welch > SHARED_COHERENCE_FLOOR)
    _check("max_coherence_multitaper>0.5", inp.max_coherence_multitaper > SHARED_COHERENCE_FLOOR)
    _check("max_z_score>3", inp.max_z_score > Z_SCORE_FLOOR)
    _check("empirical_p<0.01", inp.empirical_p_value < EMPIRICAL_P_LIMIT)
    _check("wavelet_persistent_band", inp.wavelet_persistent_band)
    _check("segment_robustness_pass", inp.segment_robustness_pass)
    _check("no_repetition", not inp.repetition_detected)
    _check("nan_rate_bnsyn<0.05", inp.nan_rate_bnsyn < NAN_RATE_LIMIT)
    _check("estimator_agreement", inp.estimator_agreement)
    return passed, failed


def _weak_triggered(inp: VerdictInputs) -> list[str]:
    reasons: list[str] = []
    if WEAK_COHERENCE_RANGE[0] <= inp.max_coherence_welch < WEAK_COHERENCE_RANGE[1]:
        reasons.append(f"welch_coherence_in_weak_range={inp.max_coherence_welch:.3f}")
    if WEAK_COHERENCE_RANGE[0] <= inp.max_coherence_multitaper < WEAK_COHERENCE_RANGE[1]:
        reasons.append(f"mt_coherence_in_weak_range={inp.max_coherence_multitaper:.3f}")
    if WEAK_Z_RANGE[0] <= inp.max_z_score < WEAK_Z_RANGE[1]:
        reasons.append(f"z_in_weak_range={inp.max_z_score:.2f}")
    if not inp.frequency_stable:
        reasons.append("peak_frequency_shifted_from_v1")
    if not inp.physical_frequency_match:
        reasons.append("physical_frequency_mismatch")
    if not inp.estimator_agreement:
        reasons.append("estimator_disagreement")
    if not inp.wavelet_persistent_band:
        reasons.append("weak_wavelet_persistence")
    return reasons


def _independent(inp: VerdictInputs) -> list[str]:
    reasons: list[str] = []
    if inp.max_coherence_welch < INDEP_COHERENCE_CEIL:
        reasons.append(f"welch_coherence<{INDEP_COHERENCE_CEIL}")
    if inp.max_coherence_multitaper < INDEP_COHERENCE_CEIL:
        reasons.append(f"mt_coherence<{INDEP_COHERENCE_CEIL}")
    if inp.max_z_score < INDEP_Z_CEIL:
        reasons.append(f"z<{INDEP_Z_CEIL}")
    if inp.empirical_p_value >= INDEP_P_FLOOR:
        reasons.append(f"p>={INDEP_P_FLOOR}")
    return reasons


def assign_verdict(inp: VerdictInputs) -> VerdictReport:
    passed, failed = _positive_gates(inp)
    # Shared: all positive gates pass.
    if not failed:
        return VerdictReport(
            label="SHARED_SPECTRAL_COMPONENT",
            reasons=("all_positive_gates_passed",),
            positive_gates_passed=tuple(passed),
            positive_gates_failed=(),
        )
    # Independent: any strong independence trigger.
    indep_reasons = _independent(inp)
    if indep_reasons:
        return VerdictReport(
            label="SPECTRALLY_INDEPENDENT",
            reasons=tuple(indep_reasons),
            positive_gates_passed=tuple(passed),
            positive_gates_failed=tuple(failed),
        )
    # Default: weak overlap.
    weak = _weak_triggered(inp)
    if not weak:
        weak = [f"missing_positive_gates={len(failed)}"]
    return VerdictReport(
        label="WEAK_SPECTRAL_OVERLAP",
        reasons=tuple(weak),
        positive_gates_passed=tuple(passed),
        positive_gates_failed=tuple(failed),
    )
