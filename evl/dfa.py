"""Detrended Fluctuation Analysis -- second independent H estimator.

DFA provides Hurst exponent H as independent check against PSD slope.
gamma_PSD = 2H + 1 (VERIFIED formula).

If DFA and PSD disagree -> signal is non-stationary or corrupted.
Agreement -> stronger evidence for regime classification.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np
from scipy.stats import theilslopes


def dfa_exponent(
    signal: np.ndarray,
    min_box: int = 8,
    max_box_ratio: float = 0.25,
    n_scales: int = 20,
) -> float | None:
    """Compute DFA scaling exponent (Hurst-like).

    Args:
        signal:        1D time series
        min_box:       minimum box size
        max_box_ratio: max box as fraction of signal length
        n_scales:      number of log-spaced scales

    Returns:
        H (float) or None if insufficient data.
        H ~ 0.5: uncorrelated (white noise)
        H > 0.5: persistent (long memory)
        H < 0.5: anti-persistent
    """
    signal = np.asarray(signal, dtype=np.float64).ravel()
    N = len(signal)
    if 4 * min_box > N:
        return None

    max_box = int(N * max_box_ratio)
    if max_box < min_box + 4:
        return None

    # Cumulative sum of detrended signal (profile)
    profile = np.cumsum(signal - signal.mean())

    # Log-spaced box sizes
    scales = np.unique(np.logspace(np.log10(min_box), np.log10(max_box), n_scales).astype(int))
    scales = scales[scales >= min_box]
    if len(scales) < 4:
        return None

    fluctuations = []
    for s in scales:
        n_boxes = N // s
        if n_boxes < 1:
            continue
        rms_values = []
        for i in range(n_boxes):
            segment = profile[i * s : (i + 1) * s]
            # Linear detrend within box
            x = np.arange(s, dtype=np.float64)
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            rms = np.sqrt(np.mean((segment - trend) ** 2))
            rms_values.append(rms)
        if rms_values:
            fluctuations.append(np.mean(rms_values))
        else:
            fluctuations.append(np.nan)

    scales_valid = scales[: len(fluctuations)]
    fluct = np.array(fluctuations)

    # Remove NaN/zero
    mask = np.isfinite(fluct) & (fluct > 0) & (scales_valid > 0)
    if mask.sum() < 4:
        return None

    log_s = np.log10(scales_valid[mask].astype(float))
    log_f = np.log10(fluct[mask])

    # Theil-Sen robust slope
    slope, _, _, _ = theilslopes(log_f, log_s)
    return float(slope)


def dfa_validate_psd(
    signal: np.ndarray,
    psd_beta: float,
    tolerance: float = 0.5,
) -> dict:
    """Cross-validate DFA Hurst exponent against PSD beta.

    gamma_PSD = 2H + 1, so H = (gamma_PSD - 1) / 2 = (beta - 1) / 2.
    DFA gives H directly. If they agree within tolerance -> consistent.
    """
    H_dfa = dfa_exponent(signal)
    if H_dfa is None:
        return {"status": "DFA_FAILED", "H_dfa": None}

    H_psd = (psd_beta - 1.0) / 2.0  # from beta = 2H + 1
    gamma_dfa = 2 * H_dfa + 1
    delta_H = abs(H_dfa - H_psd)
    consistent = delta_H < tolerance

    return {
        "status": "OK",
        "H_dfa": round(H_dfa, 4),
        "H_psd": round(H_psd, 4),
        "gamma_dfa": round(gamma_dfa, 4),
        "gamma_psd": round(psd_beta, 4),
        "delta_H": round(delta_H, 4),
        "consistent": consistent,
    }
