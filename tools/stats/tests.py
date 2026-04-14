"""Hypothesis tests — Welch's t, Mann-Whitney U, permutation.

Every test returns a :class:`TestResult` with the test statistic, the
degrees of freedom (where applicable), and a **two-sided** p-value.
One-sided p-values are deliberately absent: experimentalists almost
always report two-sided, and the code that enforces a two-sided
discipline avoids a class of motivated-reasoning bugs.

References
----------
* Welch 1947, *Biometrika* 34:28. Satterthwaite–Welch approximation.
* Mann & Whitney 1947, *Ann. Math. Stat.* 18:50. Rank-sum test.
* Fisher 1935, *The Design of Experiments*, §21. Permutation principle.
"""

from __future__ import annotations

import dataclasses
import math
import random
from collections.abc import Callable, Sequence

from scipy.stats import mannwhitneyu
from scipy.stats import t as _t_dist

__all__ = ["TestResult", "mann_whitney_u", "permutation_test", "welch_t_test"]


@dataclasses.dataclass(frozen=True)
class TestResult:
    """Two-sided test result with a named test family."""

    test: str  # "welch_t" | "mann_whitney_u" | "permutation"
    statistic: float
    df: float | None  # degrees of freedom (None for MWU / permutation)
    p_value: float  # two-sided
    n_a: int
    n_b: int
    extra: dict[str, float | int] = dataclasses.field(default_factory=dict)

    def as_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "test": self.test,
            "statistic": round(self.statistic, 4),
            "p_value": _round_pval(self.p_value),
            "n_a": self.n_a,
            "n_b": self.n_b,
        }
        if self.df is not None:
            out["df"] = round(self.df, 2)
        if self.extra:
            out["extra"] = {
                k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.extra.items()
            }
        return out


def _round_pval(p: float) -> float:
    """Preserve small p-values with 2 significant digits; round larger to 4 dp."""

    if not math.isfinite(p):
        return float(p)
    if p < 1e-4:
        return float(f"{p:.2e}")
    return round(p, 4)


# ---------------------------------------------------------------------------
# Welch's t
# ---------------------------------------------------------------------------
def welch_t_test(a: Sequence[float], b: Sequence[float]) -> TestResult:
    """Two-sided Welch's t-test with Satterthwaite df.

    Implements the Welch 1947 approximation:

        t  = (mean(a) - mean(b)) / sqrt(var(a)/n_a + var(b)/n_b)
        df = (var(a)/n_a + var(b)/n_b)^2 /
             [(var(a)/n_a)^2/(n_a-1) + (var(b)/n_b)^2/(n_b-1)]

    The two-sided p-value uses the Student-t survival function at
    ``|t|`` with ``df`` degrees of freedom (``scipy.stats.t.sf``).
    """

    a = list(a)
    b = list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        raise ValueError(f"Welch's t needs ≥2 samples per group; got {na}, {nb}")
    ma = sum(a) / na
    mb = sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se2 = va / na + vb / nb
    if se2 <= 0.0:
        raise ValueError("zero variance in both groups — Welch's t is undefined")
    t = (ma - mb) / math.sqrt(se2)
    df = se2**2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    p = 2.0 * float(_t_dist.sf(abs(t), df))
    return TestResult(
        test="welch_t",
        statistic=t,
        df=df,
        p_value=p,
        n_a=na,
        n_b=nb,
    )


# ---------------------------------------------------------------------------
# Mann-Whitney U
# ---------------------------------------------------------------------------
def mann_whitney_u(a: Sequence[float], b: Sequence[float]) -> TestResult:
    """Two-sided Mann-Whitney U / Wilcoxon rank-sum test.

    Delegates to ``scipy.stats.mannwhitneyu`` with
    ``alternative='two-sided'`` and ``method='auto'`` (exact for small
    samples, normal approximation with tie correction for large ones).
    """

    a = list(a)
    b = list(b)
    if len(a) == 0 or len(b) == 0:
        raise ValueError("Mann-Whitney U needs non-empty samples")
    stat, p = mannwhitneyu(a, b, alternative="two-sided", method="auto")
    u_a = float(stat)
    u_b = float(len(a) * len(b) - u_a)
    return TestResult(
        test="mann_whitney_u",
        statistic=u_a,
        df=None,
        p_value=float(p),
        n_a=len(a),
        n_b=len(b),
        extra={"u_statistic_b": u_b, "u_min": min(u_a, u_b)},
    )


# ---------------------------------------------------------------------------
# Permutation test
# ---------------------------------------------------------------------------
def permutation_test(
    a: Sequence[float],
    b: Sequence[float],
    statistic: Callable[[Sequence[float], Sequence[float]], float],
    *,
    n_permutations: int,
    seed: int,
) -> TestResult:
    """Exchangeability permutation test for an arbitrary two-sample statistic.

    Estimates Pr(|T(π)| ≥ |T(obs)|) under H₀ of exchangeability
    between the two groups, with a Monte-Carlo permutation sample of
    size ``n_permutations``. Reports the Davison-Hinkley (1997 §4.3)
    conservative p-value ``(k + 1) / (n + 1)``.
    """

    a = list(a)
    b = list(b)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("permutation test needs ≥2 per group")
    if n_permutations < 50:
        raise ValueError(f"n_permutations must be ≥50; got {n_permutations}")

    t_obs = float(statistic(a, b))
    combined = a + b
    na = len(a)
    rng = random.Random(seed)

    k = 0
    for _ in range(n_permutations):
        rng.shuffle(combined)
        t_star = float(statistic(combined[:na], combined[na:]))
        if abs(t_star) >= abs(t_obs):
            k += 1
    p = (k + 1) / (n_permutations + 1)
    return TestResult(
        test="permutation",
        statistic=t_obs,
        df=None,
        p_value=p,
        n_a=na,
        n_b=len(b),
        extra={"n_permutations": n_permutations, "n_extreme": k},
    )
