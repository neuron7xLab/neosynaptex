"""Causality battery — spec §V.

Propagation A → B is declared TRUE iff ALL of the following hold:

* Granger p < 0.01 robust across lags (reuses core.granger_multilag)
* Transfer entropy z-score > 3.0 vs shuffled null (n ≥ 500)
* Cascade lag stable across bootstrap blocks (σ_lag / mean_lag < 15%)
* Jitter survival ≥ 0.75
* Effect size > baseline drift

Each function here returns raw diagnostics; verdict logic lives in
`verdict.py`. Stationarity prechecks live in `stationarity()` below.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.granger_multilag import granger_multilag
from formal.dcvp.alignment import apply_jitter, dtw_align

__all__ = [
    "StationarityReport",
    "stationarity",
    "transfer_entropy",
    "te_null",
    "cascade_lag",
    "granger_robust",
    "jitter_survival",
    "effect_size",
    "baseline_drift",
]


@dataclass(frozen=True)
class StationarityReport:
    is_stationary: bool
    first_second_half_drift: float
    nan_fraction: float
    snr: float


def stationarity(x: np.ndarray, snr_floor: float = 0.5) -> StationarityReport:
    """Lightweight ADF-free stationarity + signal-health check.

    We enforce differencing upstream when needed; this check is a gate
    that refuses to score pathological inputs (NaN floods, dead signal).
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n == 0:
        return StationarityReport(False, float("inf"), 1.0, 0.0)
    nan_frac = float(np.mean(~np.isfinite(x)))
    if nan_frac > 0.05:
        return StationarityReport(False, float("inf"), nan_frac, 0.0)
    clean = x[np.isfinite(x)]
    if clean.size < 4:
        return StationarityReport(False, float("inf"), nan_frac, 0.0)
    half = clean.size // 2
    m1, m2 = float(np.mean(clean[:half])), float(np.mean(clean[half:]))
    s = float(np.std(clean)) + 1e-12
    drift = abs(m1 - m2) / s
    # Crude SNR: variance of signal vs variance of one-step noise.
    noise_var = float(np.var(np.diff(clean))) + 1e-12
    sig_var = float(np.var(clean)) + 1e-12
    snr = sig_var / noise_var
    is_stat = drift < 0.5 and snr > snr_floor
    return StationarityReport(is_stat, drift, nan_frac, snr)


def _discretize(x: np.ndarray, n_bins: int = 8) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x.astype(np.int64)
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi <= lo:
        return np.zeros_like(x, dtype=np.int64)
    edges = np.linspace(lo, hi, n_bins + 1)
    edges[-1] += 1e-9
    return np.clip(np.digitize(x, edges) - 1, 0, n_bins - 1)


def transfer_entropy(
    source: np.ndarray,
    target: np.ndarray,
    lag: int = 1,
    n_bins: int = 6,
) -> float:
    """Binned Shannon TE(source → target) with k=l=1 histories.

    TE = H(Y_t+1 | Y_t) - H(Y_t+1 | Y_t, X_t)
    """
    s = _discretize(source, n_bins)
    t = _discretize(target, n_bins)
    n = min(len(s), len(t)) - lag
    if n < 8:
        return 0.0
    y_past = t[:n]
    y_fut = t[lag : lag + n]
    x_past = s[:n]

    def _entropy(hist: np.ndarray) -> float:
        total = hist.sum()
        if total == 0:
            return 0.0
        p = hist.astype(np.float64) / total
        nz = p[p > 0]
        return float(-np.sum(nz * np.log(nz)))

    joint_yy = np.zeros((n_bins, n_bins), dtype=np.int64)
    joint_yxy = np.zeros((n_bins, n_bins, n_bins), dtype=np.int64)
    y_marg = np.zeros(n_bins, dtype=np.int64)
    yx_marg = np.zeros((n_bins, n_bins), dtype=np.int64)
    for a, b, c in zip(y_past, y_fut, x_past, strict=True):
        joint_yy[a, b] += 1
        joint_yxy[a, c, b] += 1
        y_marg[a] += 1
        yx_marg[a, c] += 1

    h_y = _entropy(y_marg)
    h_yy = _entropy(joint_yy.ravel())
    h_yx = _entropy(yx_marg.ravel())
    h_yxy = _entropy(joint_yxy.ravel())
    te = (h_yy - h_y) - (h_yxy - h_yx)
    return float(max(te, 0.0))


def te_null(
    source: np.ndarray,
    target: np.ndarray,
    n_surrogates: int,
    rng: np.random.Generator,
    lag: int = 1,
    n_bins: int = 6,
) -> tuple[float, float, float]:
    """Return (observed_TE, null_mean, null_std) from time-shuffled surrogates."""
    obs = transfer_entropy(source, target, lag=lag, n_bins=n_bins)
    nulls = np.empty(n_surrogates, dtype=np.float64)
    src_copy = np.asarray(source, dtype=np.float64).copy()
    for i in range(n_surrogates):
        perm = rng.permutation(src_copy)
        nulls[i] = transfer_entropy(perm, target, lag=lag, n_bins=n_bins)
    return obs, float(np.mean(nulls)), float(np.std(nulls) + 1e-12)


def granger_robust(
    source: np.ndarray,
    target: np.ndarray,
    max_lag: int,
    seed: int,
    n_surrogate: int = 199,
) -> tuple[float, int]:
    """Return (p_value, selected_lag) from BIC-selected multilag Granger.

    Uses surrogate-based p-value from core.granger_multilag: the source
    series is permuted `n_surrogate` times and p is the rank of the
    observed F-statistic in the null distribution. 199 surrogates give
    enough resolution to detect p < 0.01 while staying fast.
    """
    result = granger_multilag(
        np.asarray(source, dtype=np.float64),
        np.asarray(target, dtype=np.float64),
        max_lag=max_lag,
        n_surrogate=n_surrogate,
        seed=seed,
    )
    raw_p = result.get("p_value", 1.0)
    try:
        p = float(raw_p) if raw_p is not None else 1.0
    except (TypeError, ValueError):
        p = 1.0
    raw_lag = result.get("lag_selected", 1)
    try:
        lag = int(raw_lag) if raw_lag is not None else 1
    except (TypeError, ValueError):
        lag = 1
    return p, lag


def cascade_lag(
    a: np.ndarray,
    b: np.ndarray,
    max_lag: int,
    n_blocks: int = 8,
) -> tuple[int, float]:
    """Return (mean_lag, coefficient_of_variation_of_lag).

    Estimates argmax cross-correlation lag on blocks of the signal;
    the CV of the lag across blocks is the stability metric σ_lag.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = min(len(a), len(b))
    if n < max_lag * 3:
        return 0, float("inf")
    block = n // n_blocks
    if block < max_lag * 2:
        return 0, float("inf")
    lags = np.empty(n_blocks, dtype=np.float64)
    for i in range(n_blocks):
        seg_a = a[i * block : (i + 1) * block]
        seg_b = b[i * block : (i + 1) * block]
        sa = seg_a - seg_a.mean()
        sb = seg_b - seg_b.mean()
        best_lag, best_val = 0, -np.inf
        for lag in range(1, max_lag + 1):
            v = float(np.dot(sa[:-lag], sb[lag:]))
            if v > best_val:
                best_val, best_lag = v, lag
        lags[i] = best_lag
    mean = float(np.mean(lags))
    std = float(np.std(lags))
    cv = std / (abs(mean) + 1e-9)
    return int(round(mean)), float(cv)


def jitter_survival(
    source: np.ndarray,
    target: np.ndarray,
    max_shift: int,
    dropout: float,
    rng: np.random.Generator,
    n_trials: int = 16,
    granger_lag: int = 3,
) -> float:
    """Fraction of jittered trials in which Granger p<0.01 still holds."""
    passes = 0
    for i in range(n_trials):
        s_j = apply_jitter(source, max_shift, dropout, rng)
        t_j = apply_jitter(target, max_shift, dropout, rng)
        p, _ = granger_robust(s_j, t_j, max_lag=granger_lag, seed=int(rng.integers(0, 2**31 - 1)))
        if p < 0.01:
            passes += 1
    return passes / n_trials


def effect_size(a: np.ndarray, b: np.ndarray) -> float:
    """Normalized coupling strength via aligned correlation."""
    a_al, b_al, _ = dtw_align(a, b)
    if a_al.size < 4:
        return 0.0
    a_z = (a_al - a_al.mean()) / (a_al.std() + 1e-12)
    b_z = (b_al - b_al.mean()) / (b_al.std() + 1e-12)
    return float(abs(np.mean(a_z * b_z)))


def baseline_drift(x: np.ndarray) -> float:
    """Long-run drift magnitude used as effect-size floor."""
    x = np.asarray(x, dtype=np.float64)
    if x.size < 4:
        return 0.0
    half = x.size // 2
    m1, m2 = float(np.mean(x[:half])), float(np.mean(x[half:]))
    s = float(np.std(x)) + 1e-12
    return abs(m1 - m2) / s
