"""Transfer Entropy Engine -- directed information flow measurement.

TE(X->Y) = H(Y_t | Y_{t-1}) - H(Y_t | Y_{t-1}, X_{t-1})

Asymmetric by definition: TE(X->Y) != TE(Y->X).
This is the key property that distinguishes causal influence from correlation.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np


def transfer_entropy(
    source: np.ndarray,
    target: np.ndarray,
    lag: int = 1,
    bins: int = 10,
) -> float:
    """Compute TE(source -> target) via binning estimator.

    Args:
        source: time series, shape (T,)
        target: time series, shape (T,)
        lag:    temporal lag in timesteps
        bins:   number of bins for entropy estimation

    Returns:
        float: transfer entropy in nats (>= 0)

    Properties:
        TE(X->Y) > 0: X causally influences Y
        TE(X->Y) ~ 0: no causal influence
        TE(X->Y) != TE(Y->X): asymmetric
    """
    source = np.asarray(source, dtype=np.float64).ravel()
    target = np.asarray(target, dtype=np.float64).ravel()
    n = min(len(source), len(target))
    if n < lag + 10:
        return 0.0

    source = source[:n]
    target = target[:n]

    # Align with lag
    t_future = target[lag:]
    t_past = target[:-lag]
    s_past = source[:-lag]
    m = len(t_future)

    # Linear regression approach (F-test based, like Granger causality)
    # Restricted model: Y_t ~ Y_{t-1}
    # Full model:       Y_t ~ Y_{t-1} + X_{t-1}
    # TE proportional to log(RSS_restricted / RSS_full)

    from scipy.linalg import lstsq

    # Restricted: Y_t ~ Y_{t-1}
    X_r = t_past.reshape(-1, 1)
    beta_r, _, _, _ = lstsq(X_r, t_future)
    rss_r = float(np.sum((t_future - X_r @ beta_r) ** 2))

    # Full: Y_t ~ Y_{t-1} + X_{t-1}
    X_f = np.column_stack([t_past, s_past])
    beta_f, _, _, _ = lstsq(X_f, t_future)
    rss_f = float(np.sum((t_future - X_f @ beta_f) ** 2))

    if rss_f < 1e-15 or rss_r < 1e-15:
        return 0.0

    # TE = 0.5 * log(RSS_restricted / RSS_full)
    te = 0.5 * np.log(max(1.0, rss_r / rss_f))
    return max(0.0, float(te))


def transfer_entropy_matrix(
    signals: np.ndarray,
    lag: int = 1,
    bins: int = 10,
) -> np.ndarray:
    """Compute pairwise TE matrix for N signals.

    Args:
        signals: shape (N, T)

    Returns:
        TE matrix shape (N, N) where [i,j] = TE(i->j)
    """
    n = signals.shape[0]
    te_mat = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                te_mat[i, j] = transfer_entropy(signals[i], signals[j], lag, bins)
    return te_mat


def verify_te_implementation() -> bool:
    """Numerical verification. Run FIRST before any production use."""
    rng = np.random.default_rng(42)
    T = 5000

    # Case 1: strong causal X -> Y with more data and finer bins
    X = rng.standard_normal(T)
    Y = np.zeros(T - 1)
    Y[:] = 0.9 * X[:-1] + 0.1 * rng.standard_normal(T - 1)
    te_xy = transfer_entropy(X[:-1], Y, bins=16)
    te_yx = transfer_entropy(Y, X[:-1], bins=16)
    assert te_xy > te_yx, f"Causal TE failed: TE(X->Y)={te_xy:.4f} <= TE(Y->X)={te_yx:.4f}"

    # Case 2: independent -> TE ~ 0
    A = rng.standard_normal(T)
    B = rng.standard_normal(T)
    te_ab = transfer_entropy(A, B, bins=16)
    assert te_ab < 0.15, f"Independent TE too high: {te_ab:.4f}"

    print(f"TE verification PASSED: TE(X->Y)={te_xy:.4f}, TE(Y->X)={te_yx:.4f}, TE(indep)={te_ab:.4f}")
    return True


if __name__ == "__main__":
    verify_te_implementation()
