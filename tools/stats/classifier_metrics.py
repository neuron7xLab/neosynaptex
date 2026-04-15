"""Confidence intervals for binary-classification metrics.

Wraps three primitives:

* :func:`wilson_interval` — CI for a binomial proportion (accuracy,
  sensitivity, specificity).
* :func:`auc_with_hanley_mcneil_ci` — AUC with analytical SE from
  Hanley & McNeil 1982.
* :func:`bootstrap_metric_ci` — stratified-resampling bootstrap CI
  for any user-supplied classifier metric.

References
----------
* Wilson 1927, *JASA* 22:209. Score-interval formula for a proportion.
* Hanley & McNeil 1982, *Radiology* 143:29. AUC / Mann-Whitney SE.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

from scipy.stats import norm as _norm

__all__ = ["auc_with_hanley_mcneil_ci", "bootstrap_metric_ci", "wilson_interval"]


def wilson_interval(
    successes: int, trials: int, *, confidence: float = 0.95
) -> tuple[float, float, float]:
    """Wilson score CI for a binomial proportion.

    Robust to small sample sizes and to p̂ at the boundary 0/1,
    where the classical Wald interval collapses. Returns
    ``(p_hat, ci_low, ci_high)``.
    """

    if not 0 <= successes <= trials:
        raise ValueError(f"need 0 ≤ successes ({successes}) ≤ trials ({trials})")
    if trials <= 0:
        raise ValueError("trials must be ≥1")
    p = successes / trials
    z = float(_norm.ppf(0.5 + confidence / 2.0))
    denom = 1.0 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials)
    lo = max(0.0, (centre - margin) / denom)
    hi = min(1.0, (centre + margin) / denom)
    return p, lo, hi


def auc_with_hanley_mcneil_ci(
    scores_positive: Sequence[float],
    scores_negative: Sequence[float],
    *,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """AUC and analytical CI per Hanley & McNeil 1982.

    A = Pr(X_+ > X_-) + 0.5 · Pr(X_+ = X_-)  via the Mann-Whitney U.
    Variance:
        Q₁ = A / (2 − A)
        Q₂ = 2 A² / (1 + A)
        Var(A) = [A(1 − A) + (n_+ − 1)(Q₁ − A²) + (n_- − 1)(Q₂ − A²)]
                 / (n_+ · n_-)
    Returns ``(auc, ci_low, ci_high)``.
    """

    pos = list(scores_positive)
    neg = list(scores_negative)
    if len(pos) == 0 or len(neg) == 0:
        raise ValueError("AUC needs non-empty positive and negative groups")

    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    n_pos = len(pos)
    n_neg = len(neg)
    auc = wins / (n_pos * n_neg)

    q1 = auc / (2.0 - auc) if auc < 2.0 else 0.0
    q2 = 2.0 * auc * auc / (1.0 + auc) if (1.0 + auc) > 0 else 0.0
    var = (auc * (1.0 - auc) + (n_pos - 1) * (q1 - auc * auc) + (n_neg - 1) * (q2 - auc * auc)) / (
        n_pos * n_neg
    )
    var = max(var, 0.0)
    se = math.sqrt(var)
    z = float(_norm.ppf(0.5 + confidence / 2.0))
    return auc, max(0.0, auc - z * se), min(1.0, auc + z * se)


def bootstrap_metric_ci(
    y_true: Sequence[int],
    scores: Sequence[float],
    metric: Callable[[Sequence[int], Sequence[float]], float],
    *,
    n_boot: int,
    seed: int,
    confidence: float = 0.95,
    stratified: bool = True,
) -> tuple[float, float, float]:
    """Stratified percentile-bootstrap CI for any classifier metric.

    Default is class-stratified resampling: each bootstrap replicate
    preserves the per-class sample size from the original cohort.
    This keeps sensitivity, specificity, and AUC well-defined on
    every replicate (an un-stratified bootstrap can draw an all-
    positive sample and collapse specificity).
    """

    y = list(y_true)
    s = list(scores)
    if len(y) != len(s):
        raise ValueError("y_true and scores must be parallel")
    if n_boot < 100:
        raise ValueError(f"n_boot must be ≥100; got {n_boot}")

    point = float(metric(y, s))
    rng = random.Random(seed)

    if stratified:
        pos_idx = [i for i, v in enumerate(y) if v == 1]
        neg_idx = [i for i, v in enumerate(y) if v == 0]
        if len(pos_idx) < 2 or len(neg_idx) < 2:
            raise ValueError("stratified bootstrap needs ≥2 per class")

    reps: list[float] = []
    for _ in range(n_boot):
        if stratified:
            draw_p = [pos_idx[rng.randrange(len(pos_idx))] for _ in range(len(pos_idx))]
            draw_n = [neg_idx[rng.randrange(len(neg_idx))] for _ in range(len(neg_idx))]
            idx = draw_p + draw_n
        else:
            idx = [rng.randrange(len(y)) for _ in range(len(y))]
        y_b = [y[i] for i in idx]
        s_b = [s[i] for i in idx]
        try:
            reps.append(float(metric(y_b, s_b)))
        except (ValueError, ZeroDivisionError):
            continue
    if len(reps) < 0.5 * n_boot:
        raise RuntimeError(f"too many degenerate bootstrap draws ({len(reps)}/{n_boot})")
    reps.sort()
    alpha = 1.0 - confidence
    lo_idx = int(math.floor(alpha / 2.0 * len(reps)))
    hi_idx = int(math.ceil((1.0 - alpha / 2.0) * len(reps))) - 1
    return point, reps[lo_idx], reps[hi_idx]
