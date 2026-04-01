"""Fractal Dynamics V2: spectral evolution + DFA Hurst + basin invariant.

Ref: Kantelhardt et al. (2002) Physica A 316:87-114 (DFA)
     Peng et al. (1994) Phys Rev E 49:1685
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .fractal_arsenal import compute_multifractal_spectrum

__all__ = [
    "BasinInvariantResult",
    "DFAResult",
    "FractalDynamicsReport",
    "SpectralEvolution",
    "compute_basin_invariant",
    "compute_dfa",
    "compute_spectral_evolution",
]

# FRACTAL DYNAMICS V2


@dataclass
class SpectralEvolution:
    """Temporal evolution of multifractal spectrum width delta_alpha(t).

    Tracks how system complexity changes over time:
      d(delta_alpha)/dt > 0: expansion — system building complexity
      delta_alpha → 0: collapse — monofractalization → critical transition

    Ref: Kantelhardt et al. (2002) Physica A 316:87-114
    """

    delta_alpha_t: np.ndarray
    d_delta_alpha_dt: np.ndarray
    timestamps: np.ndarray
    is_collapsing: bool
    collapse_onset: int | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "delta_alpha_final": round(float(self.delta_alpha_t[-1]), 4),
            "delta_alpha_max": round(float(self.delta_alpha_t.max()), 4),
            "d_da_dt_mean": round(float(np.mean(self.d_delta_alpha_dt)), 6),
            "d_da_dt_max": round(float(np.max(np.abs(self.d_delta_alpha_dt))), 6),
            "is_collapsing": self.is_collapsing,
            "collapse_onset": self.collapse_onset,
            "n_frames": len(self.delta_alpha_t),
        }


def compute_spectral_evolution(
    history: np.ndarray,
    stride: int = 1,
    q_values: np.ndarray | None = None,
) -> SpectralEvolution:
    """Track delta_alpha(t) across field history.

    Computes multifractal spectrum width at each frame, then derives
    d(delta_alpha)/dt to detect complexity expansion or collapse.

    Args:
        history: (T, N, N) field history
        stride: compute every `stride` frames (default 1)
        q_values: q-values for multifractal computation

    Returns:
        SpectralEvolution with delta_alpha trajectory and collapse detection.
    """
    T = history.shape[0]
    frames = list(range(0, T, stride))
    da_t = np.zeros(len(frames))

    for i, t in enumerate(frames):
        spec = compute_multifractal_spectrum(history[t], q_values=q_values)
        da_t[i] = spec.delta_alpha

    d_da = np.diff(da_t)
    timestamps = np.array(frames, dtype=float)

    # Collapse detection: delta_alpha decreasing over last 30% of trajectory
    tail_start = max(1, int(len(da_t) * 0.7))
    tail = da_t[tail_start:]
    is_collapsing = bool(len(tail) >= 2 and tail[-1] < tail[0] * 0.7)

    # Find onset: first frame where d_da becomes persistently negative
    collapse_onset: int | None = None
    if is_collapsing and len(d_da) >= 3:
        # Rolling window of 3: if all negative, mark onset
        for k in range(len(d_da) - 2):
            if d_da[k] < 0 and d_da[k + 1] < 0 and d_da[k + 2] < 0:
                collapse_onset = int(frames[k])
                break

    return SpectralEvolution(
        delta_alpha_t=da_t,
        d_delta_alpha_dt=d_da,
        timestamps=timestamps,
        is_collapsing=is_collapsing,
        collapse_onset=collapse_onset,
    )


@dataclass
class DFAResult:
    """Detrended Fluctuation Analysis result.

    Ref: Peng et al. (1994) Phys Rev E 49:1685
         Kantelhardt et al. (2002) Physica A 316:87-114

    H < 0.5: anti-persistent (mean-reverting)
    H = 0.5: uncorrelated (random walk)
    H > 0.5: persistent (trending, has memory)
    H → 1.0: critical slowing down — maximum persuadability window
    """

    hurst_exponent: float
    r_squared: float
    fluctuations: np.ndarray
    scales: np.ndarray
    is_persistent: bool
    is_critical: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "hurst_exponent": round(self.hurst_exponent, 4),
            "r_squared": round(self.r_squared, 4),
            "is_persistent": self.is_persistent,
            "is_critical": self.is_critical,
            "n_scales": len(self.scales),
        }


def compute_dfa(
    time_series: np.ndarray,
    min_scale: int = 4,
    max_scale: int | None = None,
    n_scales: int = 10,
) -> DFAResult:
    """Detrended Fluctuation Analysis for Hurst exponent estimation.

    Computes the scaling exponent H of a time series via:
    1. Integrate (cumulative sum of detrended signal)
    2. Divide into windows of size s
    3. Fit linear trend in each window, compute RMS of residuals F(s)
    4. H = slope of log(F) vs log(s)

    H → 1.0 signals critical slowing down = maximum persuadability.

    Args:
        time_series: 1D array (e.g., field mean over time)
        min_scale: smallest window size
        max_scale: largest window (default T//4)
        n_scales: number of log-spaced scales

    Returns:
        DFAResult with Hurst exponent and diagnostics.
    """
    from scipy.stats import linregress as _linregress

    x = np.asarray(time_series, dtype=np.float64)
    T = len(x)
    if T < 16:
        return DFAResult(
            hurst_exponent=0.5,
            r_squared=0.0,
            fluctuations=np.array([]),
            scales=np.array([]),
            is_persistent=False,
            is_critical=False,
        )

    # Integrate: cumulative sum of centered signal
    y = np.cumsum(x - np.mean(x))

    if max_scale is None:
        max_scale = T // 4
    max_scale = max(max_scale, min_scale + 1)

    scales = np.unique(np.logspace(np.log10(min_scale), np.log10(max_scale), n_scales).astype(int))
    scales = scales[scales >= min_scale]
    scales = scales[scales <= max_scale]

    if len(scales) < 3:
        return DFAResult(
            hurst_exponent=0.5,
            r_squared=0.0,
            fluctuations=np.array([]),
            scales=np.array([]),
            is_persistent=False,
            is_critical=False,
        )

    fluctuations = np.zeros(len(scales))

    for i, s in enumerate(scales):
        n_windows = T // s
        if n_windows < 1:
            fluctuations[i] = np.nan
            continue
        rms_list: list[float] = []
        for w in range(n_windows):
            segment = y[w * s : (w + 1) * s]
            # Linear detrend
            t_axis = np.arange(s, dtype=np.float64)
            coeffs = np.polyfit(t_axis, segment, 1)
            trend = np.polyval(coeffs, t_axis)
            rms_list.append(float(np.sqrt(np.mean((segment - trend) ** 2))))
        fluctuations[i] = float(np.mean(rms_list)) if rms_list else np.nan

    valid = ~np.isnan(fluctuations) & (fluctuations > 0)
    if valid.sum() < 3:
        return DFAResult(
            hurst_exponent=0.5,
            r_squared=0.0,
            fluctuations=fluctuations,
            scales=scales,
            is_persistent=False,
            is_critical=False,
        )

    log_s = np.log(scales[valid].astype(float))
    log_f = np.log(fluctuations[valid])
    reg = _linregress(log_s, log_f)
    H = float(reg.slope)
    r2 = float(reg.rvalue**2)

    return DFAResult(
        hurst_exponent=H,
        r_squared=r2,
        fluctuations=fluctuations,
        scales=scales,
        is_persistent=H > 0.55,
        is_critical=H > 0.85,
    )


@dataclass
class BasinInvariantResult:
    """S_bb x S_B anti-correlation diagnostic.

    Novel MFN invariant: basin entropy (boundary fractality) and basin
    stability (return probability) are anti-correlated near transitions.

    chi = S_bb * S_B should be approximately constant in stable regimes.
    Deviation signals topological reorganization.

    No prior publication connects Menck (2013) basin stability with
    Daza (2016) basin entropy in a single diagnostic.
    """

    S_bb: float
    S_B: float
    chi: float
    chi_interpretation: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "S_bb": round(self.S_bb, 4),
            "S_B": round(self.S_B, 4),
            "chi": round(self.chi, 4),
            "interpretation": self.chi_interpretation,
        }


def compute_basin_invariant(
    S_bb: float,
    S_B: float,
) -> BasinInvariantResult:
    """Compute the S_bb x S_B anti-correlation invariant.

    Args:
        S_bb: basin entropy from compute_basin_fractality()
        S_B: basin stability from BasinStabilityAnalyzer

    Returns:
        BasinInvariantResult with chi diagnostic.

    Interpretation:
        S_B high + S_bb low → stable, smooth boundaries (healthy)
        S_B low + S_bb high → unstable, fractal boundaries (critical)
        Both low → single-basin dominated (trivial)
        Both high → paradoxical (check data quality)
    """
    chi = S_bb * S_B

    if S_B > 0.7 and S_bb < 0.5:
        interp = "STABLE: robust basin with smooth boundaries"
    elif S_B < 0.4 and S_bb > float(np.log(2)):
        interp = "CRITICAL: fractal boundaries + low stability — intervention window"
    elif S_B < 0.4 and S_bb < 0.3:
        interp = "COLLAPSING: single basin absorbing — loss of multistability"
    elif S_B > 0.7 and S_bb > float(np.log(2)):
        interp = "PARADOX: high stability + fractal boundaries — verify data"
    else:
        interp = "TRANSITIONAL: system between regimes"

    return BasinInvariantResult(
        S_bb=S_bb,
        S_B=S_B,
        chi=chi,
        chi_interpretation=interp,
    )


@dataclass
class FractalDynamicsReport:
    """Unified report from Fractal Dynamics V2 computations."""

    spectral_evolution: SpectralEvolution
    dfa: DFAResult
    basin_invariant: BasinInvariantResult | None = None

    def summary(self) -> str:
        """Single-line summary."""
        se = self.spectral_evolution
        dfa = self.dfa
        collapse = "COLLAPSING" if se.is_collapsing else "expanding"
        critical = (
            "CRITICAL"
            if dfa.is_critical
            else ("persistent" if dfa.is_persistent else "uncorrelated")
        )
        basin = ""
        if self.basin_invariant:
            bi = self.basin_invariant
            basin = f" | chi={bi.chi:.3f} {bi.chi_interpretation.split(':')[0]}"
        return (
            f"[DYNAMICS] da(T)={se.delta_alpha_t[-1]:.3f}({collapse}) "
            f"H={dfa.hurst_exponent:.3f}({critical})"
            f"{basin}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        d: dict[str, Any] = {
            "spectral_evolution": self.spectral_evolution.to_dict(),
            "dfa": self.dfa.to_dict(),
        }
        if self.basin_invariant:
            d["basin_invariant"] = self.basin_invariant.to_dict()
        return d
