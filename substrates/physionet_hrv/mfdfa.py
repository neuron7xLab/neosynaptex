"""Multifractal Detrended Fluctuation Analysis (MFDFA) — minimal impl.

Reference: Kantelhardt et al. 2002, Physica A, doi:10.1016/S0378-4371(02)01383-3.

Algorithm:
  For each scale s ∈ [s_min, s_max] (logspaced):
    1. Y(i) = cumulative sum of (x − mean(x))   ← profile
    2. Divide Y into N_s = floor(N/s) non-overlapping segments
       (forward + backward, doubled, per Kantelhardt).
    3. Per segment v: detrend (polynomial order m) and compute
       variance F²(s, v) = mean[(Y_v − Y_v_fit)²].
    4. Generalized fluctuation function:
         F_q(s) = [ (1/(2 N_s)) Σ_v F²(s,v)^(q/2) ]^(1/q)        (q ≠ 0)
         F_0(s) = exp[ (1/(4 N_s)) Σ_v ln(F²(s,v)) ]              (q = 0)
  For each q:
    Fit F_q(s) ~ s^h(q) on log-log; h(q) = generalized Hurst.
    τ(q) = q·h(q) − 1
  Multifractal spectrum:
    α(q) = dτ/dq    (numerical derivative)
    f(α) = q·α − τ(q)

Multifractal width:
  Δh = max(h) − min(h)
  Δα = max(α) − min(α)

Interpretation:
  Δh ≈ 0  → monofractal (single scaling exponent)
  Δh > 0  → multifractal (range of scaling exponents)

Narrow Δh on cardiac HRV ⇒ simple stable scaling regime.
Wide Δh ⇒ rich multi-regime dynamics (e.g., autonomic switching).
"""

from __future__ import annotations

import dataclasses

import numpy as np

__all__ = ["MFDFAResult", "mfdfa", "mfdfa_width"]


@dataclasses.dataclass(frozen=True)
class MFDFAResult:
    """Output of one MFDFA run on a 1-D signal."""

    q_values: np.ndarray
    scales: np.ndarray
    hq: np.ndarray  # h(q): generalized Hurst exponent at each q
    tau: np.ndarray  # τ(q) = q·h(q) − 1
    alpha: np.ndarray  # singularity strength α(q) = dτ/dq
    f_alpha: np.ndarray  # singularity spectrum f(α)
    delta_h: float  # h(q_min) − h(q_max), classical multifractal width
    delta_alpha: float  # max(α) − min(α)
    h_at_q2: float  # h(q=2) = classical Hurst exponent
    n_samples: int
    fit_order: int


def _fluctuation(profile: np.ndarray, scale: int, fit_order: int) -> np.ndarray:
    """Per-segment detrended variance at one scale.

    Splits profile into floor(N/s) non-overlapping segments, fits a
    polynomial of given order to each, returns the variances.
    Uses both forward and backward partitioning per Kantelhardt 2002.
    """

    n = len(profile)
    n_seg = n // scale
    if n_seg < 2:
        return np.array([])
    # Forward
    fwd = profile[: n_seg * scale].reshape(n_seg, scale)
    # Backward (start from end)
    bwd = profile[n - n_seg * scale :].reshape(n_seg, scale)
    segs = np.vstack([fwd, bwd])
    x = np.arange(scale)
    variances = []
    for seg in segs:
        coeffs = np.polyfit(x, seg, fit_order)
        trend = np.polyval(coeffs, x)
        variances.append(np.mean((seg - trend) ** 2))
    return np.asarray(variances)


def mfdfa(
    x: np.ndarray,
    *,
    q_values: np.ndarray | None = None,
    s_min: int = 16,
    s_max: int | None = None,
    n_scales: int = 20,
    fit_order: int = 1,
) -> MFDFAResult:
    """Run MFDFA on a 1-D signal.

    Parameters
    ----------
    x : array-like
        Input signal.
    q_values : array-like, optional
        Moment orders. Default: 21 values from -5 to 5 step 0.5.
    s_min, s_max, n_scales : int
        Scale range and count (logspaced).
    fit_order : int
        Polynomial detrend order (1 = linear).
    """

    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 100:
        raise ValueError(f"signal too short for MFDFA: n={n}")

    if q_values is None:
        q_values = np.arange(-5.0, 5.5, 0.5)
    q_values = np.asarray(q_values, dtype=np.float64)
    if 0.0 in q_values:
        # avoid division by zero; replace 0 with tiny epsilon for the
        # q=0 branch below.
        pass

    if s_max is None:
        s_max = n // 4
    scales = np.unique(
        np.round(np.logspace(np.log10(s_min), np.log10(s_max), n_scales)).astype(int)
    )
    scales = scales[scales >= s_min]

    profile = np.cumsum(x - x.mean())

    # F²(s, v) per scale; aggregate across q.
    # F_q(s) is a 2D array (n_q × n_scales).
    fq_matrix = np.zeros((len(q_values), len(scales)))
    for j, s in enumerate(scales):
        var = _fluctuation(profile, int(s), fit_order)
        if len(var) == 0:
            fq_matrix[:, j] = np.nan
            continue
        for i, q in enumerate(q_values):
            if q == 0.0:
                fq_matrix[i, j] = float(np.exp(0.5 * np.mean(np.log(var))))
            else:
                fq_matrix[i, j] = float(np.mean(var ** (q / 2)) ** (1.0 / q))

    # Fit F_q(s) ~ s^h(q) on log-log per q.
    log_s = np.log(scales.astype(float))
    hq = np.zeros(len(q_values))
    for i in range(len(q_values)):
        log_fq = np.log(fq_matrix[i])
        valid = np.isfinite(log_fq)
        if valid.sum() < 3:
            hq[i] = np.nan
            continue
        slope, _ = np.polyfit(log_s[valid], log_fq[valid], 1)
        hq[i] = float(slope)

    tau = q_values * hq - 1.0
    # Singularity strength α = dτ/dq via central differences
    alpha = np.gradient(tau, q_values)
    f_alpha = q_values * alpha - tau

    valid_h = hq[np.isfinite(hq)]
    delta_h = float(valid_h.max() - valid_h.min()) if len(valid_h) > 0 else float("nan")
    valid_a = alpha[np.isfinite(alpha)]
    delta_alpha = float(valid_a.max() - valid_a.min()) if len(valid_a) > 0 else float("nan")
    # h at q = 2 (classical Hurst)
    idx_q2 = int(np.argmin(np.abs(q_values - 2.0)))
    h_at_q2 = float(hq[idx_q2])

    return MFDFAResult(
        q_values=q_values,
        scales=scales,
        hq=hq,
        tau=tau,
        alpha=alpha,
        f_alpha=f_alpha,
        delta_h=round(delta_h, 4),
        delta_alpha=round(delta_alpha, 4),
        h_at_q2=round(h_at_q2, 4),
        n_samples=n,
        fit_order=fit_order,
    )


def mfdfa_width(x: np.ndarray, **kwargs: object) -> tuple[float, float]:
    """Convenience: return (Δh, h(q=2)) only."""

    r = mfdfa(x, **kwargs)  # type: ignore[arg-type]
    return r.delta_h, r.h_at_q2
