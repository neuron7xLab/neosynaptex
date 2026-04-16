"""Shared fidelity/discrimination metrics for null-family screening.

All families use these helpers so the screening comparison is
apples-to-apples. No family-specific shortcuts are permitted.

Protocol: NULL-SCREEN-v1.1.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as _sig  # type: ignore[import-untyped]

# NOTE: we intentionally import ``mfdfa`` lazily inside ``compute_delta_h``.
# The module path ``substrates.physionet_hrv.mfdfa`` is measurement-branch
# code (NULL-SCREEN-v1.1: do not touch) and contains a pre-existing
# untyped ``**kwargs`` signature at ``mfdfa_width`` that would surface
# under ``mypy core/ --strict`` the moment this import is resolved at
# module load. Deferring the import keeps the mypy scan for ``core/``
# closed at this boundary without modifying the measurement branch.

__all__ = [
    "ACF_LAGS_MAX",
    "acf_rmse",
    "compute_delta_h",
    "distribution_error",
    "log_psd_rmse",
    "psd_one_sided",
]

ACF_LAGS_MAX: int = 64


def psd_one_sided(x: np.ndarray, fs: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """One-sided PSD via Welch; consistent across all families."""
    n = len(x)
    nperseg = max(8, min(256, n // 4))
    f, p = _sig.welch(x, fs=fs, nperseg=nperseg)
    return f, p


def log_psd_rmse(x: np.ndarray, y: np.ndarray) -> float:
    """RMSE between log10(PSD(x)) and log10(PSD(y)) over positive bins."""
    _, p_x = psd_one_sided(x)
    _, p_y = psd_one_sided(y)
    n = min(len(p_x), len(p_y))
    p_x = p_x[:n]
    p_y = p_y[:n]
    mask = (p_x > 0) & (p_y > 0)
    if not np.any(mask):
        return float("inf")
    return float(np.sqrt(np.mean((np.log10(p_x[mask]) - np.log10(p_y[mask])) ** 2)))


def _acf(x: np.ndarray, max_lag: int = ACF_LAGS_MAX) -> np.ndarray:
    """Biased autocorrelation at lags 1..max_lag (unit-variance normalised)."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    var = float(np.mean(x * x)) + 1e-30
    out = np.empty(max_lag, dtype=np.float64)
    n = len(x)
    for k in range(1, max_lag + 1):
        out[k - 1] = float(np.mean(x[: n - k] * x[k:])) / var
    return out


def acf_rmse(x: np.ndarray, y: np.ndarray, max_lag: int = ACF_LAGS_MAX) -> float:
    """RMSE between the ACF of x and the ACF of y at lags 1..max_lag."""
    ax = _acf(x, max_lag=max_lag)
    ay = _acf(y, max_lag=max_lag)
    return float(np.sqrt(np.mean((ax - ay) ** 2)))


def distribution_error(x: np.ndarray, y: np.ndarray) -> float:
    """Max absolute difference between sorted multisets. Zero iff exact."""
    n = min(len(x), len(y))
    return float(np.max(np.abs(np.sort(np.asarray(x)[:n]) - np.sort(np.asarray(y)[:n]))))


def compute_delta_h(
    x: np.ndarray,
    *,
    q_values: np.ndarray | None = None,
    s_min: int = 16,
    s_max: int | None = None,
    n_scales: int = 20,
    fit_order: int = 1,
) -> float:
    """Δh from the measurement-branch ``mfdfa`` call. Do NOT rescale here.

    Scale window defaults to ``(16, n//4)``, compatible with both short
    synthetics (4096 samples) and real NSR records (≥50k samples).
    """
    # Deferred import — see the top-of-module NOTE.
    from substrates.physionet_hrv.mfdfa import mfdfa  # noqa: PLC0415

    if q_values is None:
        q_values = np.arange(-5.0, 5.5, 0.5)
    n = len(x)
    if s_max is None:
        s_max = max(s_min + 1, n // 4)
    res = mfdfa(
        x,
        q_values=q_values,
        s_min=s_min,
        s_max=s_max,
        n_scales=n_scales,
        fit_order=fit_order,
    )
    return float(res.delta_h)
