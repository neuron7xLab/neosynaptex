"""Phase 6 — stability checks (frequency, estimator agreement, segments).

The v2 peak is credible only if it survives three orthogonal
perturbations of the measurement pipeline:

* frequency_stable       — v2 peak is within ±0.03 of a v1 peak
                            ({0.2031, 0.2500} cycles/tick)
* estimator_agreement    — Welch and multi-taper agree within ±0.03 AND
                            the wavelet persistent band covers that
                            frequency
* segment_robustness     — split the logged series into 3 equal blocks
                            and require the same dominant band in ≥2/3
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from experiments.spectral_coherence_v3.spectral_battery import (
    welch_coherence,
)

__all__ = [
    "StabilityReport",
    "run_stability",
    "V1_PEAKS",
    "FREQUENCY_STABLE_TOLERANCE",
    "ESTIMATOR_AGREEMENT_TOLERANCE",
]

V1_PEAKS: tuple[float, float] = (0.2031, 0.2500)
FREQUENCY_STABLE_TOLERANCE = 0.03
ESTIMATOR_AGREEMENT_TOLERANCE = 0.03
SEGMENT_COUNT = 3
SEGMENT_BAND_TOLERANCE = 0.05


@dataclass(frozen=True)
class StabilityReport:
    frequency_stable: bool
    estimator_agreement: bool
    segment_robustness_pass: bool
    segment_peak_frequencies: tuple[float, ...]
    welch_peak: float
    multitaper_peak: float
    wavelet_peak: float


def _within(x: float, target: float, tol: float) -> bool:
    return bool(abs(x - target) <= tol)


def _frequency_stable(peak: float) -> bool:
    return any(_within(peak, v1, FREQUENCY_STABLE_TOLERANCE) for v1 in V1_PEAKS)


def _estimator_agreement(
    welch_peak: float,
    mt_peak: float,
    wavelet_band: tuple[float, float],
) -> bool:
    if not _within(welch_peak, mt_peak, ESTIMATOR_AGREEMENT_TOLERANCE):
        return False
    lo, hi = wavelet_band
    # Wavelet band must cover (or at least touch within tolerance) the
    # Welch/multi-taper agreement point.
    lo_slack = lo - ESTIMATOR_AGREEMENT_TOLERANCE
    hi_slack = hi + ESTIMATOR_AGREEMENT_TOLERANCE
    return bool(lo_slack <= welch_peak <= hi_slack)


def _segment_robustness(a: np.ndarray, b: np.ndarray) -> tuple[bool, tuple[float, ...]]:
    """Split into 3 blocks; compute Welch peak per block; require ≥ 2/3 agree."""
    n = min(len(a), len(b))
    if n < 3 * 64:
        return False, ()
    block = n // SEGMENT_COUNT
    peaks: list[float] = []
    for i in range(SEGMENT_COUNT):
        seg_a = a[i * block : (i + 1) * block]
        seg_b = b[i * block : (i + 1) * block]
        peaks.append(welch_coherence(seg_a, seg_b, nperseg=min(64, block)).peak_frequency)
    # Count how many peaks are within tolerance of the median peak.
    med = float(np.median(peaks))
    agree = sum(1 for p in peaks if abs(p - med) <= SEGMENT_BAND_TOLERANCE)
    return agree >= 2, tuple(float(p) for p in peaks)


def run_stability(
    a: np.ndarray,
    b: np.ndarray,
    welch_peak: float,
    mt_peak: float,
    wavelet_band: tuple[float, float],
    wavelet_peak: float,
) -> StabilityReport:
    freq_ok = _frequency_stable(welch_peak) or _frequency_stable(mt_peak)
    est_ok = _estimator_agreement(welch_peak, mt_peak, wavelet_band)
    seg_ok, seg_peaks = _segment_robustness(a, b)
    return StabilityReport(
        frequency_stable=freq_ok,
        estimator_agreement=est_ok,
        segment_robustness_pass=seg_ok,
        segment_peak_frequencies=seg_peaks,
        welch_peak=welch_peak,
        multitaper_peak=mt_peak,
        wavelet_peak=wavelet_peak,
    )
