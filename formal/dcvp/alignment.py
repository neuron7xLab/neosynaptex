"""Dynamic time warping + jitter robustness — spec §III.

Substrates A and B run asynchronously in independent processes, so their
γ streams must be aligned before causality can be measured. We use a
classical O(N·M) DTW with Sakoe–Chiba band to keep the alignment local,
then quantify alignment sensitivity under jitter.

`jitter_survival` and `alignment_sensitivity` feed back into the
causality verdict logic in verdict.py.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "dtw_align",
    "alignment_sensitivity",
    "apply_jitter",
]


def _sakoe_chiba_cost(a: np.ndarray, b: np.ndarray, band: int) -> np.ndarray:
    n, m = len(a), len(b)
    # Band must be wide enough to absorb the length mismatch, otherwise
    # the warping path cannot reach (n, m) at all.
    band = max(band, abs(n - m) + 1)
    inf = np.inf
    d = np.full((n + 1, m + 1), inf, dtype=np.float64)
    d[0, 0] = 0.0
    for i in range(1, n + 1):
        j_lo = max(1, i - band)
        j_hi = min(m, i + band)
        for j in range(j_lo, j_hi + 1):
            cost = (a[i - 1] - b[j - 1]) ** 2
            d[i, j] = cost + min(d[i - 1, j], d[i, j - 1], d[i - 1, j - 1])
    return d


def _backtrack(d: np.ndarray) -> list[tuple[int, int]]:
    i, j = d.shape[0] - 1, d.shape[1] - 1
    path: list[tuple[int, int]] = []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        prev = min(d[i - 1, j], d[i, j - 1], d[i - 1, j - 1])
        if prev == d[i - 1, j - 1]:
            i, j = i - 1, j - 1
        elif prev == d[i - 1, j]:
            i -= 1
        else:
            j -= 1
    path.reverse()
    return path


def dtw_align(
    a: np.ndarray, b: np.ndarray, band_frac: float = 0.1
) -> tuple[np.ndarray, np.ndarray, float]:
    """Align two 1-D γ series with DTW.

    Returns (a_aligned, b_aligned, normalized_cost). Aligned series have
    equal length — for each warped path step we take the pair (a[i], b[j]).
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        return a, b, float("inf")
    band = max(1, int(round(band_frac * max(len(a), len(b)))))
    d = _sakoe_chiba_cost(a, b, band)
    cost = float(d[-1, -1]) / (len(a) + len(b))
    path = _backtrack(d)
    if not path:
        return a, b, cost
    a_al = np.array([a[i] for i, _ in path], dtype=np.float64)
    b_al = np.array([b[j] for _, j in path], dtype=np.float64)
    return a_al, b_al, cost


def apply_jitter(
    x: np.ndarray,
    max_shift: int,
    dropout: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply random ±tick shifts and sample dropout.

    Implemented as per-sample random resampling from a local neighborhood
    plus Bernoulli masking filled by nearest-neighbor.
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n == 0:
        return x
    shifts = rng.integers(-max_shift, max_shift + 1, size=n)
    idx = np.clip(np.arange(n) + shifts, 0, n - 1)
    y = x[idx]
    if dropout > 0.0:
        mask = rng.random(n) < dropout
        if mask.any():
            good = np.where(~mask)[0]
            if good.size == 0:
                return y
            # Nearest-neighbor fill for dropped samples.
            for i in np.where(mask)[0]:
                nearest = good[np.argmin(np.abs(good - i))]
                y[i] = y[nearest]
    return y


def alignment_sensitivity(
    a: np.ndarray,
    b: np.ndarray,
    max_shift: int,
    dropout: float,
    rng: np.random.Generator,
    n_trials: int = 16,
) -> float:
    """Return the bounded drift of DTW cost under jitter, in [0, 1].

    Metric: mean of |cost_jittered − cost_base| / (cost_base + var_scale),
    where ``var_scale = var(a) + var(b)`` keeps the denominator away from
    zero when two signals happen to match perfectly. Squashed through
    ``tanh`` so the result is bounded.
    """
    _, _, base = dtw_align(a, b)
    if not np.isfinite(base):
        return 1.0
    var_scale = float(np.var(a)) + float(np.var(b)) + 1e-9
    rel: list[float] = []
    for _ in range(n_trials):
        a_j = apply_jitter(a, max_shift, dropout, rng)
        b_j = apply_jitter(b, max_shift, dropout, rng)
        _, _, c = dtw_align(a_j, b_j)
        if np.isfinite(c):
            rel.append(abs(c - base) / (base + var_scale))
    if not rel:
        return 1.0
    return float(np.tanh(np.mean(rel)))
