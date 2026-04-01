"""Criticality Detector — SOC + phase transition fingerprinting.

Detects whether the R-D system operates near a critical point by measuring:
1. Power-law distribution of cluster sizes (SOC signature)
2. Divergence of correlation length ξ
3. Critical slowing down (autocorrelation time τ)
4. Susceptibility χ (variance amplification)

Systems at criticality maximize information processing capacity (Langton 1990,
Beggs & Plenz 2003). Turing patterns self-organize to near-criticality.

First R-D framework with built-in criticality classification.
Ref: Bak (1996), Sornette (2006), Mora & Bialek (2011) J. Stat. Phys.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label

__all__ = ["CriticalityFingerprint", "detect_criticality"]


@dataclass
class CriticalityFingerprint:
    """Fingerprint of critical-state proximity."""

    power_law_exponent: float  # τ in P(s) ~ s^(-τ). SOC: τ ∈ [1.5, 2.5]
    power_law_r2: float  # quality of power-law fit
    correlation_length: float  # ξ — spatial correlation length (pixels)
    susceptibility: float  # χ = N·Var(m) — order parameter fluctuation
    autocorrelation_time: float  # τ_ac — critical slowing down indicator
    criticality_score: float  # [0, 1] — composite criticality proximity
    verdict: str  # "subcritical", "critical", "supercritical", "edge_of_chaos"

    def summary(self) -> str:
        return (
            f"[CRIT] {self.verdict} score={self.criticality_score:.3f} "
            f"τ={self.power_law_exponent:.2f} ξ={self.correlation_length:.1f} "
            f"χ={self.susceptibility:.3f}"
        )


def _cluster_size_distribution(field: np.ndarray) -> np.ndarray:
    """Extract cluster sizes from binarized field."""
    binary = (field > np.median(field)).astype(int)
    labeled, n_clusters = label(binary)
    if n_clusters == 0:
        return np.array([1])
    sizes = np.array([np.sum(labeled == i) for i in range(1, n_clusters + 1)])
    return sizes[sizes > 0]


def _fit_power_law(sizes: np.ndarray) -> tuple[float, float]:
    """Fit P(s) ~ s^(-τ) via log-log regression. Returns (τ, R²)."""
    if len(sizes) < 5:
        return 0.0, 0.0

    unique, counts = np.unique(sizes, return_counts=True)
    if len(unique) < 3:
        return 0.0, 0.0

    log_s = np.log(unique.astype(float))
    log_p = np.log(counts.astype(float) / counts.sum())

    coeffs = np.polyfit(log_s, log_p, 1)
    tau = -coeffs[0]  # negative slope = exponent

    predicted = np.polyval(coeffs, log_s)
    ss_res = np.sum((log_p - predicted) ** 2)
    ss_tot = np.sum((log_p - np.mean(log_p)) ** 2)
    r2 = max(0.0, 1.0 - ss_res / (ss_tot + 1e-12))

    return float(tau), float(r2)


def _correlation_length(field: np.ndarray) -> float:
    """Spatial correlation length via autocorrelation decay."""
    u = field - np.mean(field)
    var = float(np.var(u))
    if var < 1e-12:
        return 0.0

    f_u = np.fft.fft2(u)
    power = np.abs(f_u) ** 2
    acf = np.real(np.fft.ifft2(power)) / (var * u.size)

    # Radial average of ACF
    N = field.shape[0]
    center = N // 2
    y, x = np.ogrid[:N, :N]
    r = np.sqrt((x - center) ** 2 + (y - center) ** 2).astype(int)
    acf_shifted = np.fft.fftshift(acf)

    max_r = N // 4
    radial_acf = np.zeros(max_r)
    for ri in range(max_r):
        mask = r == ri
        if mask.any():
            radial_acf[ri] = float(np.mean(acf_shifted[mask]))

    # Find where ACF drops below 1/e
    threshold = radial_acf[0] / np.e if radial_acf[0] > 0 else 0
    xi = 1.0
    for ri in range(1, max_r):
        if radial_acf[ri] < threshold:
            xi = float(ri)
            break
    else:
        xi = float(max_r)

    return xi


def detect_criticality(
    field: np.ndarray,
    history: np.ndarray | None = None,
) -> CriticalityFingerprint:
    """Detect proximity to critical state.

    Args:
        field: current 2D field
        history: optional (T, N, N) for temporal autocorrelation
    """
    # 1. Power-law cluster distribution
    sizes = _cluster_size_distribution(field)
    tau, r2 = _fit_power_law(sizes)

    # 2. Correlation length
    xi = _correlation_length(field)

    # 3. Susceptibility (order parameter variance)
    N = field.size
    float(np.mean(field))
    chi = float(N * np.var(field))

    # 4. Autocorrelation time (if history available)
    tau_ac = 0.0
    if history is not None and history.shape[0] >= 10:
        ts = np.array([float(np.mean(history[t])) for t in range(history.shape[0])])
        ts_centered = ts - np.mean(ts)
        var_ts = float(np.var(ts_centered))
        if var_ts > 1e-12:
            acf_ts = np.correlate(ts_centered, ts_centered, mode="full")
            acf_ts = acf_ts[len(acf_ts) // 2 :]
            acf_ts = acf_ts / (acf_ts[0] + 1e-12)
            # τ_ac = first crossing of 1/e
            for i in range(1, len(acf_ts)):
                if acf_ts[i] < 1.0 / np.e:
                    tau_ac = float(i)
                    break
            else:
                tau_ac = float(len(acf_ts))

    # 5. Composite criticality score
    # SOC signature: τ ∈ [1.5, 2.5] with good R²
    score_tau = max(0, 1.0 - abs(tau - 2.0) / 1.5) * min(r2, 1.0)
    # Long correlation: ξ > N/10 indicates criticality
    score_xi = min(1.0, xi / (field.shape[0] / 5))
    # High susceptibility
    score_chi = min(1.0, chi / (N * 0.01 + 1e-12))
    # Critical slowing down
    score_tau_ac = min(1.0, tau_ac / 10.0) if tau_ac > 0 else 0.0

    criticality_score = float(np.mean([score_tau, score_xi, score_chi, score_tau_ac]))

    # Classify
    if criticality_score > 0.7:
        verdict = "critical"
    elif criticality_score > 0.5:
        verdict = "edge_of_chaos"
    elif criticality_score > 0.3:
        verdict = "supercritical"
    else:
        verdict = "subcritical"

    return CriticalityFingerprint(
        power_law_exponent=tau,
        power_law_r2=r2,
        correlation_length=xi,
        susceptibility=chi,
        autocorrelation_time=tau_ac,
        criticality_score=criticality_score,
        verdict=verdict,
    )
