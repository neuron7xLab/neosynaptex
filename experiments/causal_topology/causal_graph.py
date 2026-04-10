"""Granger-causality directed graphs over state variables.

For each rolling window of per-tick state observations we build a
directed graph whose edges encode pairwise Granger causality between
state variables. Edge weight is the F-statistic of the Granger test
(higher ⇒ stronger evidence of directed dependence).

We deliberately use a small, fast Granger implementation rather than
pulling in statsmodels — the test runs 4×4 = 12 directional pairs per
tick and must scale to 2000 ticks × 2 substrates × rolling window.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
from scipy.linalg import lstsq as scipy_lstsq
from scipy.stats import f as f_dist

__all__ = [
    "CausalGraphExtractor",
    "GrangerEdgeResult",
    "granger_test",
]


@dataclass(frozen=True)
class GrangerEdgeResult:
    source: str
    target: str
    f_stat: float
    p_value: float
    lag: int


def granger_test(
    source: np.ndarray,
    target: np.ndarray,
    lag: int = 1,
) -> tuple[float, float]:
    """F-test for x Granger-causing y at a fixed lag.

    Fits y[t] on (y[t-lag..1]) restricted vs (y[t-lag..1], x[t-lag..1])
    unrestricted, then reports the F statistic + p value. Returns
    (0.0, 1.0) when the window is too short or the least-squares fit
    is singular.
    """
    x = np.asarray(source, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    n = min(len(x), len(y))
    if n < 2 * lag + 5:
        return 0.0, 1.0
    x = x[:n]
    y = y[:n]

    y_target = y[lag:]
    n_obs = len(y_target)
    cols_r = [y[lag - k : n - k] for k in range(1, lag + 1)]
    cols_f = []
    for k in range(1, lag + 1):
        cols_f.append(y[lag - k : n - k])
        cols_f.append(x[lag - k : n - k])
    X_r = np.column_stack(cols_r)
    X_f = np.column_stack(cols_f)

    k_r = X_r.shape[1]
    k_f = X_f.shape[1]
    if n_obs <= k_f + 2:
        return 0.0, 1.0

    try:
        b_r, _, _, _ = scipy_lstsq(X_r, y_target)
        b_f, _, _, _ = scipy_lstsq(X_f, y_target)
    except Exception:
        return 0.0, 1.0

    rss_r = float(np.sum((y_target - X_r @ b_r) ** 2))
    rss_f = float(np.sum((y_target - X_f @ b_f) ** 2))
    if rss_f < 1e-15:
        return 0.0, 1.0

    df1 = k_f - k_r
    df2 = n_obs - k_f
    if df1 <= 0 or df2 <= 0:
        return 0.0, 1.0

    f_stat = ((rss_r - rss_f) / df1) / (rss_f / df2)
    if not np.isfinite(f_stat) or f_stat <= 0.0:
        return 0.0, 1.0
    p_value = float(f_dist.sf(f_stat, df1, df2))
    return float(f_stat), p_value


class CausalGraphExtractor:
    """Build a Granger-based directed graph from a rolling state window.

    Parameters
    ----------
    window : int
        Number of trailing observations used for each Granger test.
    max_lag : int
        Maximum lag (the extractor tries 1..max_lag and keeps the
        lowest-p lag per edge).
    alpha : float
        Significance threshold; edges with p ≥ alpha are dropped.
    """

    def __init__(self, window: int = 32, max_lag: int = 3, alpha: float = 0.05) -> None:
        if window < 8:
            raise ValueError("window must be ≥ 8 for meaningful Granger tests")
        self.window = int(window)
        self.max_lag = int(max_lag)
        self.alpha = float(alpha)

    def extract(self, state_history: list[dict[str, float]]) -> nx.DiGraph:
        """Return the directed causal graph for the most recent `window` rows.

        `state_history` is a list of state dictionaries — one per tick,
        each with the SAME set of keys. Values are cast to float.
        """
        if not state_history:
            return nx.DiGraph()
        trailing = state_history[-self.window :]
        if len(trailing) < self.window // 2:
            return nx.DiGraph()
        keys = sorted(trailing[0].keys())
        n_vars = len(keys)
        if n_vars < 2:
            g = nx.DiGraph()
            g.add_nodes_from(keys)
            return g

        data = np.array([[row.get(k, np.nan) for k in keys] for row in trailing], dtype=np.float64)
        # Drop rows containing any NaN so Granger sees a clean window.
        mask = np.all(np.isfinite(data), axis=1)
        data = data[mask]
        if data.shape[0] < max(8, 2 * self.max_lag + 5):
            g = nx.DiGraph()
            g.add_nodes_from(keys)
            return g

        g = nx.DiGraph()
        g.add_nodes_from(keys)
        for i, src in enumerate(keys):
            for j, tgt in enumerate(keys):
                if i == j:
                    continue
                best_f, best_p, best_lag = 0.0, 1.0, 1
                for lag in range(1, self.max_lag + 1):
                    f_stat, p_value = granger_test(data[:, i], data[:, j], lag=lag)
                    if p_value < best_p:
                        best_f, best_p, best_lag = f_stat, p_value, lag
                if best_p < self.alpha and best_f > 0.0:
                    g.add_edge(src, tgt, weight=best_f, p_value=best_p, lag=best_lag)
        return g
