"""Early Warning Signal (EWS) detection for critical transitions.

Detects approaching regime transitions by monitoring:
- Autocorrelation lag-1 increase (critical slowing down)
- Variance increase (flickering)
- Skewness shift (asymmetric fluctuations)

References:
    Scheffer et al. (2009) Nature 461:53-59
    Dakos et al. (2012) PLoS ONE 7:e41010
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.types.ews import CriticalTransitionWarning

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

__all__ = ["early_warning"]

# EWS thresholds (calibrated against canonical profiles)
_EWS_AUTOCORR_THRESHOLD: float = 0.85  # lag-1 autocorrelation approaching 1
_EWS_VARIANCE_RATIO_THRESHOLD: float = 2.0  # variance doubling
_EWS_SCORE_WEIGHTS: dict[str, float] = {
    "autocorrelation": 0.30,
    "variance_ratio": 0.25,
    "skewness_shift": 0.15,
    "field_range_expansion": 0.15,
    "thermodynamic": 0.15,
}


def _lag1_autocorrelation(series: np.ndarray) -> float:
    """Compute lag-1 autocorrelation of a 1D time series."""
    if len(series) < 3:
        return 0.0
    mean = np.mean(series)
    centered = series - mean
    var = np.sum(centered**2)
    if var < 1e-15:
        return 0.0
    autocov = np.sum(centered[:-1] * centered[1:])
    return float(np.clip(autocov / var, -1.0, 1.0))


def _estimate_transition_time(ews_score: float, n_steps: int) -> float:
    """Estimate steps to transition based on EWS score trend."""
    if ews_score < 0.1:
        return float("inf")
    # Simple inverse estimate: higher score = closer transition
    remaining_frac = max(0.01, 1.0 - ews_score)
    return float(n_steps * remaining_frac / ews_score)


def _classify_transition(
    autocorr: float,
    variance_ratio: float,
    skewness_late: float,
    field_range_ratio: float,
) -> str:
    """Classify the type of approaching transition."""
    if autocorr > 0.9 and variance_ratio > 2.0:
        return "critical_slowing"
    if variance_ratio > 3.0:
        return "flickering"
    if abs(skewness_late) > 1.0:
        return "asymmetric_fluctuation"
    if field_range_ratio > 1.5:
        return "turing_instability"
    if autocorr > 0.7:
        return "approaching_transition"
    return "stable"


def early_warning(seq: FieldSequence) -> CriticalTransitionWarning:
    """Detect early warning signals of critical transitions.

    Analyzes the temporal evolution of field statistics to detect
    signatures of approaching regime shifts (critical slowing down,
    flickering, asymmetric fluctuations).

    Parameters
    ----------
    seq : FieldSequence
        Must have history (3D array of shape [T, N, N]).

    Returns
    -------
    CriticalTransitionWarning
        EWS score, transition type, estimated time, and indicator breakdown.
    """
    if seq.history is None or seq.history.shape[0] < 4:
        return CriticalTransitionWarning(
            ews_score=0.0,
            transition_type="stable",
            time_to_transition=float("inf"),
            confidence=0.0,
            causal_certificate="insufficient_history",
        )

    history = seq.history
    n_steps = history.shape[0]

    # Compute per-step statistics
    means = np.array([float(np.mean(history[t])) for t in range(n_steps)])
    stds = np.array([float(np.std(history[t])) for t in range(n_steps)])
    ranges = np.array([float(np.max(history[t]) - np.min(history[t])) for t in range(n_steps)])

    # Indicator 1: Lag-1 autocorrelation of spatial mean (critical slowing down)
    autocorr = _lag1_autocorrelation(means)

    # Indicator 2: Variance ratio (late half / early half)
    mid = n_steps // 2
    var_early = float(np.mean(stds[:mid] ** 2)) + 1e-15
    var_late = float(np.mean(stds[mid:] ** 2)) + 1e-15
    variance_ratio = var_late / var_early

    # Indicator 3: Skewness in late window
    late_fields = history[mid:]
    late_flat = late_fields.reshape(-1)
    mean_late = float(np.mean(late_flat))
    std_late = float(np.std(late_flat))
    if std_late > 1e-15:
        skewness_late = float(np.mean(((late_flat - mean_late) / std_late) ** 3))
    else:
        skewness_late = 0.0

    # Indicator 4: Field range expansion
    range_early = float(np.mean(ranges[:mid])) + 1e-15
    range_late = float(np.mean(ranges[mid:])) + 1e-15
    field_range_ratio = range_late / range_early

    # Indicator 5: Thermodynamic — M(t) instability via KL divergence rate
    # dH/dt oscillation signals thermodynamic instability without importing unified_score
    kl_rates = []
    for t in range(max(1, n_steps - 5), n_steps):
        a_t = history[t].ravel().astype(np.float64)
        a_t = a_t - a_t.min() + 1e-12
        a_t = a_t / a_t.sum()
        b_t = history[t - 1].ravel().astype(np.float64)
        b_t = b_t - b_t.min() + 1e-12
        b_t = b_t / b_t.sum()
        kl_rates.append(float(np.sum(a_t * np.log(a_t / b_t))))
    thermo_instability = float(np.std(kl_rates) / (np.mean(kl_rates) + 1e-12)) if kl_rates else 0.0

    # Normalize indicators to [0, 1]
    autocorr_norm = float(np.clip((autocorr - 0.5) / 0.5, 0.0, 1.0))  # 0.5→0, 1.0→1
    variance_norm = float(np.clip((variance_ratio - 1.0) / 3.0, 0.0, 1.0))  # 1→0, 4→1
    skewness_norm = float(np.clip(abs(skewness_late) / 2.0, 0.0, 1.0))  # 0→0, 2→1
    range_norm = float(np.clip((field_range_ratio - 1.0) / 2.0, 0.0, 1.0))  # 1→0, 3→1
    thermo_norm = float(np.clip(thermo_instability / 2.0, 0.0, 1.0))  # 0→0, 2→1

    # Composite EWS score
    ews_score = (
        _EWS_SCORE_WEIGHTS["autocorrelation"] * autocorr_norm
        + _EWS_SCORE_WEIGHTS["variance_ratio"] * variance_norm
        + _EWS_SCORE_WEIGHTS["skewness_shift"] * skewness_norm
        + _EWS_SCORE_WEIGHTS["field_range_expansion"] * range_norm
        + _EWS_SCORE_WEIGHTS["thermodynamic"] * thermo_norm
    )
    ews_score = float(np.clip(ews_score, 0.0, 1.0))

    # Classify transition type
    transition_type = _classify_transition(
        autocorr, variance_ratio, skewness_late, field_range_ratio
    )

    # Estimate time to transition
    time_to_transition = _estimate_transition_time(ews_score, n_steps)

    # Confidence based on history length and signal strength
    confidence = float(np.clip(min(n_steps / 20.0, 1.0) * (0.3 + 0.7 * ews_score), 0.0, 1.0))

    # Causal certificate: hash of the indicators for reproducibility
    cert_data = f"{autocorr:.6f}:{variance_ratio:.6f}:{skewness_late:.6f}:{field_range_ratio:.6f}"
    causal_certificate = hashlib.sha256(cert_data.encode()).hexdigest()[:16]

    return CriticalTransitionWarning(
        ews_score=round(ews_score, 4),
        transition_type=transition_type,
        time_to_transition=round(time_to_transition, 1),
        confidence=round(confidence, 4),
        causal_certificate=causal_certificate,
        indicators={
            "autocorrelation_lag1": round(autocorr, 4),
            "variance_ratio": round(variance_ratio, 4),
            "skewness_late": round(skewness_late, 4),
            "field_range_ratio": round(field_range_ratio, 4),
            "autocorr_norm": round(autocorr_norm, 4),
            "variance_norm": round(variance_norm, 4),
            "skewness_norm": round(skewness_norm, 4),
            "range_norm": round(range_norm, 4),
            "thermo_instability": round(thermo_instability, 4),
            "thermo_norm": round(thermo_norm, 4),
        },
    )
