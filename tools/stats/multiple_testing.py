"""Family-wise error and false-discovery-rate corrections.

All three corrections operate on a sequence of raw p-values and
return a sequence of **adjusted** p-values in the same input order,
each one clipped to ``[0, 1]``. A downstream caller compares the
adjusted values against the target α directly — no further rank or
index bookkeeping is required on the caller side.

References
----------
* Bonferroni 1936, *Pubbl. R. Ist. Sup. Sci. Econ. Commer. Firenze* 8:3.
* Holm 1979, *Scand. J. Stat.* 6:65. Step-down Holm-Bonferroni.
* Benjamini & Hochberg 1995, *J. R. Stat. Soc. B* 57:289. Step-up FDR.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = ["benjamini_hochberg", "bonferroni", "holm_bonferroni"]


def _validate(pvalues: Sequence[float]) -> list[float]:
    ps = list(pvalues)
    if not ps:
        raise ValueError("empty p-value list")
    for p in ps:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p-values must lie in [0, 1]; got {p}")
    return ps


def bonferroni(pvalues: Sequence[float]) -> list[float]:
    """p_adj_i = min(1, m · p_i).  FWER-controlling, no monotonicity fix."""

    ps = _validate(pvalues)
    m = len(ps)
    return [min(1.0, m * p) for p in ps]


def holm_bonferroni(pvalues: Sequence[float]) -> list[float]:
    """Step-down Holm-Bonferroni.

    Sort p-values ascending:  p_(1) ≤ p_(2) ≤ … ≤ p_(m).
    Raw adjusted:   q_(i) = (m − i + 1) · p_(i)       (i = 1..m)
    Enforce monotone non-decreasing:
                    q̃_(i) = max_{j ≤ i} q_(j),  then clip to [0, 1].
    Returns adjusted p-values in the caller's original order.
    """

    ps = _validate(pvalues)
    m = len(ps)
    order = sorted(range(m), key=ps.__getitem__)
    sorted_raw = [(m - rank) * ps[idx] for rank, idx in enumerate(order)]
    # Enforce monotone non-decreasing:
    running = 0.0
    sorted_adj: list[float] = []
    for v in sorted_raw:
        running = max(running, v)
        sorted_adj.append(min(1.0, running))
    out = [0.0] * m
    for rank, idx in enumerate(order):
        out[idx] = sorted_adj[rank]
    return out


def benjamini_hochberg(pvalues: Sequence[float]) -> list[float]:
    """Step-up Benjamini-Hochberg FDR.

    Sort p-values ascending:  p_(1) ≤ p_(2) ≤ … ≤ p_(m).
    Raw adjusted:   q_(i) = m / i · p_(i)
    Enforce monotone non-increasing from the top:
                    q̃_(i) = min_{j ≥ i} q_(j),  then clip to [0, 1].
    Returns adjusted p-values (commonly called "q-values" in the BH
    literature) in the caller's original order.
    """

    ps = _validate(pvalues)
    m = len(ps)
    order = sorted(range(m), key=ps.__getitem__)
    sorted_raw = [(m / (rank + 1)) * ps[idx] for rank, idx in enumerate(order)]
    # Enforce monotone non-increasing walking back from the largest:
    running = 1.0
    sorted_adj_rev: list[float] = []
    for v in reversed(sorted_raw):
        running = min(running, v)
        sorted_adj_rev.append(min(1.0, running))
    sorted_adj = list(reversed(sorted_adj_rev))
    out = [0.0] * m
    for rank, idx in enumerate(order):
        out[idx] = sorted_adj[rank]
    return out
