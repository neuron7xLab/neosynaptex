"""Strong-null surrogate generators and null-family hypothesis tests.

References:
  - IAAFT preserves target amplitude distribution and approximately preserves PSD.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import theilslopes


def iaaft_surrogate(series: np.ndarray, rng: np.random.Generator, n_iter: int = 50) -> np.ndarray:
    """Generate IAAFT surrogate preserving PSD + amplitude distribution."""
    x = np.asarray(series, dtype=np.float64)
    n = x.size
    if n < 8:
        return x.copy()
    sorted_vals = np.sort(x)
    amplitudes = np.abs(np.fft.rfft(x))
    surrogate = rng.permutation(x).astype(np.float64, copy=True)
    for _ in range(n_iter):
        phases = np.angle(np.fft.rfft(surrogate))
        surrogate = np.fft.irfft(amplitudes * np.exp(1j * phases), n=n)
        ranks = np.argsort(np.argsort(surrogate))
        surrogate = sorted_vals[ranks]
    return surrogate


def shared_phase_iaaft(
    channels: np.ndarray, rng: np.random.Generator, n_iter: int = 50
) -> np.ndarray:
    """Multivariate shared-phase IAAFT preserving cross-channel phase coupling.

    channels shape: (n_channels, n_samples)
    """
    x = np.asarray(channels, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("channels must be 2D: (n_channels, n_samples)")
    n_ch, n = x.shape
    if n < 8:
        return x.copy()

    sorted_vals = [np.sort(xi) for xi in x]
    amplitudes = [np.abs(np.fft.rfft(xi)) for xi in x]
    # One shared phase template to preserve inter-channel phase relations.
    phase_template = np.angle(np.fft.rfft(rng.permutation(x[0])))
    out = np.vstack([rng.permutation(xi) for xi in x]).astype(np.float64, copy=True)

    for _ in range(n_iter):
        for c in range(n_ch):
            out[c] = np.fft.irfft(amplitudes[c] * np.exp(1j * phase_template), n=n)
            ranks = np.argsort(np.argsort(out[c]))
            out[c] = sorted_vals[c][ranks]
    return out


def block_shuffle(series: np.ndarray, block_length: int, rng: np.random.Generator) -> np.ndarray:
    """Shuffle contiguous blocks while preserving within-block local structure."""
    x = np.asarray(series, dtype=np.float64)
    n = x.size
    if block_length < 1:
        raise ValueError("block_length must be >= 1")
    if n < block_length:
        return x.copy()
    starts = np.arange(0, n, block_length)
    blocks = [x[s : min(s + block_length, n)] for s in starts]
    rng.shuffle(blocks)
    return np.concatenate(blocks)[:n]


def null_family_test(
    log_topo: np.ndarray, log_cost: np.ndarray, n_surrogates: int = 199, seed: int = 42
) -> dict[str, dict[str, float]]:
    """Run shuffle / block-shuffle / IAAFT null families and return p-values."""
    lt = np.asarray(log_topo, dtype=np.float64)
    lc = np.asarray(log_cost, dtype=np.float64)
    if lt.shape != lc.shape:
        raise ValueError("log_topo and log_cost must have same shape")
    if lt.size < 8:
        raise ValueError("need at least 8 points")

    rng = np.random.default_rng(seed)
    slope, _, _, _ = theilslopes(lc, lt)
    observed_gamma = -float(slope)

    block_len = max(5, lt.size // 10)
    generators = {
        "shuffle": lambda: (rng.permutation(lt), rng.permutation(lc)),
        "block_shuffle": lambda: (
            block_shuffle(lt, block_len, rng),
            block_shuffle(lc, block_len, rng),
        ),
        "iaaft": lambda: (iaaft_surrogate(lt, rng), iaaft_surrogate(lc, rng)),
        "shared_phase_iaaft": lambda: tuple(
            shared_phase_iaaft(np.vstack([lt, lc]), rng)
        ),
    }

    out: dict[str, dict[str, float]] = {}
    for name, gen_fn in generators.items():
        null_gammas = np.empty(n_surrogates, dtype=np.float64)
        for i in range(n_surrogates):
            lt_s, lc_s = gen_fn()
            s, _, _, _ = theilslopes(lc_s, lt_s)
            null_gammas[i] = -float(s)
        p_val = float((np.sum(np.abs(null_gammas) >= abs(observed_gamma)) + 1) / (n_surrogates + 1))
        out[name] = {
            "p_value": p_val,
            "null_median": float(np.median(null_gammas)),
            "null_95_low": float(np.percentile(null_gammas, 2.5)),
            "null_95_high": float(np.percentile(null_gammas, 97.5)),
            "observed_gamma": observed_gamma,
        }
    return out
