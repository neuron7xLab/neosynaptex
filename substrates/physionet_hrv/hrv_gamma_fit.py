"""HRV-specific γ-fit: VLF spectral exponent on RR-intervals.

Per ``docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`` entry hrv_physionet:
* signal: RR intervals from PhysioNet NSR2DB
* method: Welch PSD on uniform-resampled RR + Theil-Sen slope
* fit_window: VLF band 0.003–0.04 Hz
* secondary: DFA α cross-validation

This is a substrate-specific γ-fit because the standard
``substrates.market_fred.gamma_fit`` operates on already-uniform
samples (FRED monthly, BTCUSDT hourly). RR intervals are NOT
uniformly sampled in time — each interval is one beat — so we
cubic-spline interpolate onto a uniform 4 Hz grid (Task Force of
ESC/NASPE 1996 standard) before applying Welch PSD.

Same null-family infrastructure (`null_comparison`) reused via
``substrates.market_fred.gamma_fit`` for shuffled/AR(1)/IAAFT.
"""

from __future__ import annotations

import dataclasses

import numpy as np
from scipy import interpolate, signal
from scipy.stats import theilslopes

__all__ = [
    "HRVGammaFit",
    "fit_hrv_gamma",
    "rr_to_uniform_4hz",
]


@dataclasses.dataclass(frozen=True)
class HRVGammaFit:
    """Result of one VLF γ-fit on an RR-interval series."""

    gamma: float
    ci_low: float
    ci_high: float
    r2: float
    n_rr: int
    n_uniform_samples: int
    n_frequencies_fit: int
    fit_freq_lo_hz: float
    fit_freq_hi_hz: float
    method_label: str


def rr_to_uniform_4hz(rr_seconds: np.ndarray, fs_uniform: float = 4.0) -> np.ndarray:
    """Cubic-spline interpolate non-uniform RR series onto uniform grid.

    The cumulative sum of RR intervals gives the time stamps of each
    beat (in seconds). Cubic-spline-interpolating the RR values at
    those times onto a uniform grid produces an evenly-sampled
    "RR(t)" signal suitable for FFT-based PSD methods.

    Per Task Force of ESC/NASPE 1996, fs=4 Hz is the canonical
    interpolation rate for HRV spectral analysis.
    """

    rr = np.asarray(rr_seconds, dtype=np.float64)
    rr = rr[np.isfinite(rr) & (rr > 0)]
    if len(rr) < 8:
        raise ValueError(f"too few RR intervals: {len(rr)}")
    t_beats = np.cumsum(rr)
    # Build a uniform time grid spanning the recording.
    t_uniform = np.arange(t_beats[0], t_beats[-1], 1.0 / fs_uniform)
    # Cubic spline through (t_beats, rr).
    cs = interpolate.CubicSpline(t_beats, rr, extrapolate=False)
    rr_uniform = cs(t_uniform)
    rr_uniform = rr_uniform[np.isfinite(rr_uniform)]
    return rr_uniform


def fit_hrv_gamma(
    rr_seconds: np.ndarray,
    *,
    fs_uniform: float = 4.0,
    fit_lo_hz: float = 0.003,
    fit_hi_hz: float = 0.04,
    nperseg: int = 1024,
    bootstrap_n: int = 500,
    seed: int = 42,
    method_label: str = "welch_psd_theilsen_vlf_band",
) -> HRVGammaFit:
    """VLF-band γ-fit on RR-intervals.

    Steps:
    1. Interpolate RR onto uniform 4 Hz grid.
    2. Welch PSD with nperseg=1024 (~256 s window at 4 Hz).
    3. Restrict to VLF band [fit_lo_hz, fit_hi_hz].
    4. Theil-Sen slope on log-log; γ = -slope.
    5. Bootstrap CI95 (resample frequency-PSD pairs).
    """

    rr_uniform = rr_to_uniform_4hz(rr_seconds, fs_uniform=fs_uniform)
    if len(rr_uniform) < nperseg:
        nperseg = max(64, len(rr_uniform) // 4)

    f, p = signal.welch(rr_uniform, fs=fs_uniform, nperseg=nperseg, detrend="constant")
    band_mask = (f >= fit_lo_hz) & (f <= fit_hi_hz) & (p > 0)
    f_fit = f[band_mask]
    p_fit = p[band_mask]
    if len(f_fit) < 5:
        raise ValueError(
            f"too few frequency bins in VLF band: {len(f_fit)} (check nperseg / fit band)"
        )

    log_f = np.log(f_fit)
    log_p = np.log(p_fit)

    slope, intercept, lo, hi = theilslopes(log_p, log_f)
    gamma = float(-slope)
    gamma_ci_lo = float(-hi)
    gamma_ci_hi = float(-lo)

    yhat = slope * log_f + intercept
    ss_r = float(np.sum((log_p - yhat) ** 2))
    ss_t = float(np.sum((log_p - log_p.mean()) ** 2))
    r2 = 1.0 - ss_r / ss_t if ss_t > 1e-12 else 0.0

    if bootstrap_n > 0:
        rng = np.random.default_rng(seed)
        boot_g: list[float] = []
        n = len(log_f)
        for _ in range(bootstrap_n):
            idx = rng.integers(0, n, size=n)
            coeffs = np.polyfit(log_f[idx], log_p[idx], 1)
            boot_g.append(float(-coeffs[0]))
        bs = sorted(boot_g)
        ci_low_b = bs[int(0.025 * len(bs))]
        ci_high_b = bs[int(0.975 * len(bs))]
        final_lo = min(gamma_ci_lo, ci_low_b)
        final_hi = max(gamma_ci_hi, ci_high_b)
    else:
        final_lo = gamma_ci_lo
        final_hi = gamma_ci_hi

    return HRVGammaFit(
        gamma=round(gamma, 4),
        ci_low=round(final_lo, 4),
        ci_high=round(final_hi, 4),
        r2=round(float(r2), 4),
        n_rr=int(len(rr_seconds)),
        n_uniform_samples=int(len(rr_uniform)),
        n_frequencies_fit=int(len(f_fit)),
        fit_freq_lo_hz=float(f_fit[0]),
        fit_freq_hi_hz=float(f_fit[-1]),
        method_label=method_label,
    )
