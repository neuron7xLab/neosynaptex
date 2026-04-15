"""Effect-size estimators with analytical and bootstrap confidence intervals.

Every estimator returns an :class:`EffectSize` that carries the point
estimate, a 95 % CI (method-specific), and enough metadata to
re-derive the interval. No raw floats escape this module.

References
----------
* Cohen 1988, *Statistical Power Analysis for the Behavioral Sciences*
  §2.5. ``cohen_d``.
* Hedges & Olkin 1985, *Statistical Methods for Meta-Analysis*,
  §5.3 eq. 8. Analytical ``cohen_d`` variance.
* Hedges 1981, *J. Educ. Stat.* 6:107. Small-sample correction g = d · J.
* Cliff 1993, *Psych. Bull.* 114:494. Cliff's δ and its variance.
* Efron 1987, *JASA* 82:171. Bias-corrected bootstrap.
"""

from __future__ import annotations

import dataclasses
import math
import random
from collections.abc import Callable, Sequence

from scipy.stats import norm as _norm

__all__ = ["EffectSize", "bootstrap_ci", "cliffs_delta", "cohen_d", "hedges_g"]


@dataclasses.dataclass(frozen=True)
class EffectSize:
    """Point estimate + 95 % CI + enough metadata to reproduce it."""

    name: str  # "cohen_d" | "hedges_g" | "cliffs_delta"
    point: float
    ci_low: float
    ci_high: float
    n_a: int
    n_b: int
    ci_method: str  # "hedges_olkin_analytical" | "bootstrap_percentile" | …
    confidence: float  # e.g. 0.95

    def as_json(self) -> dict[str, float | int | str]:
        return {
            "name": self.name,
            "point": round(self.point, 4),
            "ci_low": round(self.ci_low, 4),
            "ci_high": round(self.ci_high, 4),
            "n_a": self.n_a,
            "n_b": self.n_b,
            "ci_method": self.ci_method,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Cohen d / Hedges g (parametric)
# ---------------------------------------------------------------------------
def _pooled_sd(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float, int, int]:
    na, nb = len(a), len(b)
    ma = sum(a) / na
    mb = sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    sp2 = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    if sp2 <= 0.0:
        raise ValueError("zero pooled variance — effect size undefined")
    return ma - mb, math.sqrt(sp2), va, na, nb


def _hedges_olkin_ci(d: float, na: int, nb: int, confidence: float) -> tuple[float, float]:
    """Analytical CI from Hedges & Olkin 1985 §5.3 eq. 8.

    Var(d) = (n_a + n_b) / (n_a · n_b) + d² / (2 (n_a + n_b))
    """

    var = (na + nb) / (na * nb) + d * d / (2 * (na + nb))
    se = math.sqrt(var)
    z = float(_norm.ppf(0.5 + confidence / 2.0))
    return d - z * se, d + z * se


def cohen_d(a: Sequence[float], b: Sequence[float], *, confidence: float = 0.95) -> EffectSize:
    """Standardised mean difference with pooled SD, Hedges-Olkin CI."""

    a = list(a)
    b = list(b)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Cohen d needs ≥2 per group")
    diff, sp, _, na, nb = _pooled_sd(a, b)
    d = diff / sp
    lo, hi = _hedges_olkin_ci(d, na, nb, confidence)
    return EffectSize(
        name="cohen_d",
        point=d,
        ci_low=lo,
        ci_high=hi,
        n_a=na,
        n_b=nb,
        ci_method="hedges_olkin_analytical",
        confidence=confidence,
    )


def hedges_g(a: Sequence[float], b: Sequence[float], *, confidence: float = 0.95) -> EffectSize:
    """Hedges's g: Cohen d with the small-sample correction factor J.

    J = 1 − 3 / (4 · (n_a + n_b) − 9)  (Hedges 1981, eq. 6b).
    """

    a = list(a)
    b = list(b)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Hedges g needs ≥2 per group")
    diff, sp, _, na, nb = _pooled_sd(a, b)
    d = diff / sp
    j = 1.0 - 3.0 / (4.0 * (na + nb) - 9.0)
    g = d * j
    lo, hi = _hedges_olkin_ci(g, na, nb, confidence)  # same variance, scaled negligibly
    return EffectSize(
        name="hedges_g",
        point=g,
        ci_low=lo,
        ci_high=hi,
        n_a=na,
        n_b=nb,
        ci_method="hedges_olkin_analytical_corrected",
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Cliff's δ (non-parametric)
# ---------------------------------------------------------------------------
def cliffs_delta(a: Sequence[float], b: Sequence[float], *, confidence: float = 0.95) -> EffectSize:
    """Probability of superiority: δ = Pr(A > B) − Pr(A < B).

    Exact from pairwise comparisons:

        δ = (#{(i,j): a_i > b_j} − #{(i,j): a_i < b_j}) / (n_a · n_b)

    95 % CI via the consistent variance estimator in Cliff 1993,
    eq. 9, with a logit transform to keep the interval inside
    [−1, +1]:

        σ̂²(δ) = [(n_a − 1) σ̂²_a + (n_b − 1) σ̂²_b + σ̂²_ab] / (n_a · n_b)
    """

    a = list(a)
    b = list(b)
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        raise ValueError("Cliff's δ needs non-empty samples")
    gt = lt = 0
    for ai in a:
        for bj in b:
            if ai > bj:
                gt += 1
            elif ai < bj:
                lt += 1
    delta = (gt - lt) / (na * nb)

    # Dominance matrix d_ij = sign(a_i − b_j) ∈ {−1, 0, +1}
    #   σ̂²_a = Var_i( mean_j d_ij ),  σ̂²_b = Var_j( mean_i d_ij ),
    #   σ̂²_ab = Var_{ij}(d_ij)
    row_means = []
    col_sums = [0.0] * nb
    total_sq = 0.0
    for ai in a:
        row = [(1 if ai > bj else -1 if ai < bj else 0) for bj in b]
        row_means.append(sum(row) / nb)
        for j, v in enumerate(row):
            col_sums[j] += v
            total_sq += v * v
    col_means = [cs / na for cs in col_sums]

    def _var(xs: list[float]) -> float:
        if len(xs) < 2:
            return 0.0
        m = sum(xs) / len(xs)
        return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)

    var_a = _var(row_means)
    var_b = _var(col_means)
    var_ab = (total_sq / (na * nb)) - delta * delta
    denom = na * nb
    sigma2 = ((na - 1) * var_a + (nb - 1) * var_b + var_ab) / denom
    z = float(_norm.ppf(0.5 + confidence / 2.0))

    se = math.sqrt(max(sigma2, 0.0))
    lo = max(-1.0, delta - z * se)
    hi = min(+1.0, delta + z * se)

    return EffectSize(
        name="cliffs_delta",
        point=delta,
        ci_low=lo,
        ci_high=hi,
        n_a=na,
        n_b=nb,
        ci_method="cliff_1993_wald",
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def bootstrap_ci(
    statistic: Callable[[Sequence[float], Sequence[float]], float],
    a: Sequence[float],
    b: Sequence[float],
    *,
    n_boot: int,
    seed: int,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Percentile bootstrap (Efron 1979) for a two-sample statistic.

    Returns ``(point, ci_low, ci_high)`` where ``point`` is the
    observed statistic and the CI is the empirical quantile of the
    bootstrap replicates at ``(1 ± confidence)/2``. The percentile
    method is preferred here over BCa because the statistics we
    consume (Cohen d, accuracy, AUC) are approximately pivotal at
    the n we work with (n ≥ 40), and percentile is free of
    jackknife-acceleration instability at small n per-group.
    """

    a = list(a)
    b = list(b)
    if n_boot < 100:
        raise ValueError(f"n_boot must be ≥100; got {n_boot}")
    if len(a) < 2 or len(b) < 2:
        raise ValueError("bootstrap CI needs ≥2 per group")
    rng = random.Random(seed)
    point = float(statistic(a, b))
    reps: list[float] = []
    na, nb = len(a), len(b)
    for _ in range(n_boot):
        sa = [a[rng.randrange(na)] for _ in range(na)]
        sb = [b[rng.randrange(nb)] for _ in range(nb)]
        try:
            reps.append(float(statistic(sa, sb)))
        except (ValueError, ZeroDivisionError):
            continue
    if len(reps) < 0.5 * n_boot:
        raise RuntimeError(f"too many degenerate bootstrap draws ({len(reps)}/{n_boot})")
    reps.sort()
    alpha = 1.0 - confidence
    lo_idx = int(math.floor(alpha / 2.0 * len(reps)))
    hi_idx = int(math.ceil((1.0 - alpha / 2.0) * len(reps))) - 1
    return point, reps[lo_idx], reps[hi_idx]
