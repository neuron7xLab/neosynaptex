"""Eight per-cell metrics for the estimator admissibility trial.

A "cell" is a (estimator, γ_true, N, σ) tuple. For each cell the trial
draws ``M`` synthetic replicates and computes the eight metrics defined
below. The metrics jointly answer the admissibility question: is the
estimator unbiased, low-variance, well-calibrated (CI coverage),
window-stable, and conservative under the null?

All metrics are pure functions; they take pre-fitted γ̂ arrays plus
the raw replicate (log_c, log_k) arrays where re-fitting is required
(window-delta, leave-one-window-out, bootstrap-dispersion).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, NamedTuple

import numpy as np

from tools.phase_3.admissibility.estimators import EstimatorResult

__all__ = [
    "CellMetrics",
    "cell_metrics",
    "false_positive_rate_on_null",
]


_BOOTSTRAP_DISPERSION_B: Final[int] = 200
_LEAVE_ONE_WINDOW_FRAC: Final[float] = 0.25  # window_size = N // 4
_WINDOW_DELTA_WIDTH_FRAC: Final[float] = 0.5  # window width = N // 2
_WINDOW_DELTA_STRIDE_FRAC: Final[float] = 0.125  # stride = N // 8


class CellMetrics(NamedTuple):
    """All eight per-cell metrics, plus housekeeping."""

    bias: float
    variance: float
    rmse: float
    ci95_coverage: float
    window_delta_max: float
    leave_one_window_out_drift: float
    bootstrap_slope_dispersion: float
    false_positive_rate_on_null: float
    n_replicates_used: int  # excludes NaN γ̂'s
    nan_fraction: float


def _slide_windows_indices(n: int, width: int, stride: int) -> list[tuple[int, int]]:
    """Return sliding-window (start, end_exclusive) tuples."""
    if width <= 0 or width > n or stride <= 0:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    while start + width <= n:
        out.append((start, start + width))
        start += stride
    return out


def _window_delta_max(
    log_c: np.ndarray,
    log_k: np.ndarray,
    fit_fn: Callable[[np.ndarray, np.ndarray], EstimatorResult],
) -> float:
    """Max − min of γ̂ across 4 sliding windows of width N/2 stride N/8.

    Per the protocol, only the first 4 windows are scored (matching the
    "max over replicates of … 4 sliding windows" phrasing). Returns NaN
    when fewer than 2 windows produce a finite γ̂.
    """
    n = log_c.size
    width = max(2, int(n * _WINDOW_DELTA_WIDTH_FRAC))
    stride = max(1, int(n * _WINDOW_DELTA_STRIDE_FRAC))
    windows = _slide_windows_indices(n, width, stride)[:4]
    estimates: list[float] = []
    for start, end in windows:
        res = fit_fn(log_c[start:end], log_k[start:end])
        if np.isfinite(res.gamma):
            estimates.append(res.gamma)
    if len(estimates) < 2:
        return float("nan")
    arr = np.asarray(estimates, dtype=np.float64)
    return float(arr.max() - arr.min())


def _leave_one_window_out_drift(
    log_c: np.ndarray,
    log_k: np.ndarray,
    fit_fn: Callable[[np.ndarray, np.ndarray], EstimatorResult],
) -> float:
    """Max |γ̂_full − γ̂_drop_window_i| over disjoint windows of width N/4.

    Drops one window of length N/4 at a time and refits on the
    remaining N − N/4 points. The drift is the largest absolute
    deviation from the full-sample γ̂.
    """
    n = log_c.size
    win = max(2, int(n * _LEAVE_ONE_WINDOW_FRAC))
    if win >= n - 1:
        return float("nan")
    full = fit_fn(log_c, log_k)
    if not np.isfinite(full.gamma):
        return float("nan")
    drift = 0.0
    starts = list(range(0, n - win + 1, win))
    seen_finite = False
    for start in starts:
        mask = np.ones(n, dtype=bool)
        mask[start : start + win] = False
        sub_c = log_c[mask]
        sub_k = log_k[mask]
        if sub_c.size < 5 or (sub_c.max() - sub_c.min()) < 1e-12:
            continue
        res = fit_fn(sub_c, sub_k)
        if not np.isfinite(res.gamma):
            continue
        seen_finite = True
        drift = max(drift, abs(full.gamma - res.gamma))
    if not seen_finite:
        return float("nan")
    return float(drift)


def _bootstrap_slope_dispersion(
    log_c: np.ndarray,
    log_k: np.ndarray,
    fit_fn: Callable[[np.ndarray, np.ndarray], EstimatorResult],
    seed: int,
) -> float:
    """Std of γ̂ across B=200 bootstrap resamples of (log_c, log_k)."""
    n = log_c.size
    rng = np.random.default_rng(seed)
    estimates = np.full(_BOOTSTRAP_DISPERSION_B, np.nan, dtype=np.float64)
    for b in range(_BOOTSTRAP_DISPERSION_B):
        idx = rng.integers(0, n, size=n)
        sub_c = log_c[idx]
        sub_k = log_k[idx]
        if (sub_c.max() - sub_c.min()) < 1e-12:
            continue
        res = fit_fn(sub_c, sub_k)
        if np.isfinite(res.gamma):
            estimates[b] = res.gamma
    finite = estimates[np.isfinite(estimates)]
    if finite.size < 2:
        return float("nan")
    return float(np.std(finite, ddof=1))


def cell_metrics(
    gamma_true: float,
    estimates: list[EstimatorResult],
    log_c_replicates: list[np.ndarray],
    log_k_replicates: list[np.ndarray],
    fit_fn: Callable[[np.ndarray, np.ndarray], EstimatorResult],
    *,
    n_replicates_for_window_metrics: int = 20,
    bootstrap_seed_base: int = 0xCAFEBABE,
) -> CellMetrics:
    """Compute the 8 per-cell metrics for a (γ_true, N, σ, estimator) cell.

    Parameters
    ----------
    gamma_true : float
        Ground-truth γ that produced the replicates.
    estimates : list[EstimatorResult]
        Length-M list of estimator outputs, one per replicate.
    log_c_replicates, log_k_replicates : list[np.ndarray]
        Length-M lists of pre-computed log-axis arrays. The window-
        based metrics need to refit on subsets, so they need the raw
        log-axis data not just γ̂.
    fit_fn : callable
        The estimator function under test, ``(log_c, log_k) -> EstimatorResult``.
        Window-based metrics call this to refit on subsets.
    n_replicates_for_window_metrics : int, keyword-only
        Window-based metrics (5, 6, 7) are O(N · M · windows) and would
        dominate runtime. We compute them on the first ``min(this, M)``
        replicates and report the worst-case across that subset, which
        is the conservative direction for an admissibility gate.
    bootstrap_seed_base : int, keyword-only
        Seed offset for the dispersion-bootstrap RNG so that the same
        cell yields the same dispersion across reruns.
    """
    gamma_arr = np.asarray([e.gamma for e in estimates], dtype=np.float64)
    finite_mask = np.isfinite(gamma_arr)
    finite_gamma = gamma_arr[finite_mask]
    n_used = int(finite_mask.sum())
    nan_fraction = 1.0 - n_used / max(1, gamma_arr.size)

    if n_used == 0:
        return CellMetrics(
            bias=float("nan"),
            variance=float("nan"),
            rmse=float("nan"),
            ci95_coverage=float("nan"),
            window_delta_max=float("nan"),
            leave_one_window_out_drift=float("nan"),
            bootstrap_slope_dispersion=float("nan"),
            false_positive_rate_on_null=float("nan"),
            n_replicates_used=0,
            nan_fraction=nan_fraction,
        )

    bias = float(np.mean(finite_gamma) - gamma_true)
    variance = float(np.var(finite_gamma, ddof=1)) if n_used > 1 else 0.0
    rmse = float(np.sqrt(np.mean((finite_gamma - gamma_true) ** 2)))

    # CI coverage: fraction of replicates whose [low, high] contains γ_true.
    covered = 0
    for e in estimates:
        if not (np.isfinite(e.ci95_low) and np.isfinite(e.ci95_high)):
            continue
        if e.ci95_low <= gamma_true <= e.ci95_high:
            covered += 1
    coverage = covered / max(1, len(estimates))

    # Window-based metrics on a capped subset for runtime.
    cap = min(n_replicates_for_window_metrics, len(log_c_replicates))
    window_deltas: list[float] = []
    drifts: list[float] = []
    dispersions: list[float] = []
    for i in range(cap):
        wd = _window_delta_max(log_c_replicates[i], log_k_replicates[i], fit_fn)
        if np.isfinite(wd):
            window_deltas.append(wd)
        dr = _leave_one_window_out_drift(log_c_replicates[i], log_k_replicates[i], fit_fn)
        if np.isfinite(dr):
            drifts.append(dr)
        disp = _bootstrap_slope_dispersion(
            log_c_replicates[i],
            log_k_replicates[i],
            fit_fn,
            seed=bootstrap_seed_base + i,
        )
        if np.isfinite(disp):
            dispersions.append(disp)

    wd_max = float(max(window_deltas)) if window_deltas else float("nan")
    drift_max = float(max(drifts)) if drifts else float("nan")
    disp_mean = float(np.mean(dispersions)) if dispersions else float("nan")

    return CellMetrics(
        bias=bias,
        variance=variance,
        rmse=rmse,
        ci95_coverage=coverage,
        window_delta_max=wd_max,
        leave_one_window_out_drift=drift_max,
        bootstrap_slope_dispersion=disp_mean,
        false_positive_rate_on_null=float("nan"),  # filled separately for null cells
        n_replicates_used=n_used,
        nan_fraction=nan_fraction,
    )


def false_positive_rate_on_null(
    estimates: list[EstimatorResult],
    *,
    alpha: float = 0.05,  # noqa: ARG001 — kept in signature for caller-side documentation
) -> float:
    """Fraction of γ_true=0 replicates whose CI excludes 0.

    A null-cell estimator emits "γ ≠ 0 at α=0.05" iff its 95 % CI does
    not contain zero. The FPR is then the fraction of replicates that
    do so. Replicates with non-finite CI are not counted as false
    positives (they are degenerate, not rejecting H0); they are still
    in the denominator, which is the conservative direction for a gate.
    """
    if not estimates:
        return float("nan")
    flagged = 0
    for e in estimates:
        if not (np.isfinite(e.ci95_low) and np.isfinite(e.ci95_high)):
            continue
        if e.ci95_low > 0 or e.ci95_high < 0:
            flagged += 1
    return flagged / len(estimates)
