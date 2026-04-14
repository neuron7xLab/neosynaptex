"""Two-cohort contrast primitives: Welch's t, Cohen's d, panel roll-up.

Pure stdlib. No numpy, no scipy — contrast logic is simple enough that
depending on scientific stacks for it would bury the algebra. The
baseline panel and MFDFA cohort modules that own the *values* depend
on numpy/scipy; this module only consumes finite floats.

Functions
---------
- :func:`welch_t`       — two-sided Welch's t with Satterthwaite df.
- :func:`cohen_d`       — pooled-SD standardised mean difference.
- :func:`contrast`      — one-call summary of a single metric contrast.
- :func:`contrast_panel`— sweep :func:`contrast` across many metrics.

All statistics are reported to four decimal places for deterministic
JSON diffing; raw full-precision values are available via the returned
``ContrastResult`` dataclass.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Iterable, Mapping
from statistics import mean, stdev

__all__ = ["ContrastResult", "cohen_d", "contrast", "contrast_panel", "welch_t"]


@dataclasses.dataclass(frozen=True)
class ContrastResult:
    """One metric, two groups — the Welch/Cohen summary."""

    n_a: int
    n_b: int
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float
    welch_t: float
    welch_df: float
    cohen_d: float

    def as_json(self) -> dict[str, float | int]:
        return {
            "n_a": self.n_a,
            "n_b": self.n_b,
            "mean_a": round(self.mean_a, 4),
            "mean_b": round(self.mean_b, 4),
            "std_a": round(self.std_a, 4),
            "std_b": round(self.std_b, 4),
            "welch_t": round(self.welch_t, 3),
            "welch_df": round(self.welch_df, 1),
            "cohen_d": round(self.cohen_d, 3),
        }


def welch_t(a: Iterable[float], b: Iterable[float]) -> tuple[float, float]:
    """Two-sided Welch's t with Satterthwaite degrees of freedom."""

    a = list(a)
    b = list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        raise ValueError(f"need ≥2 samples per group; got {na}, {nb}")
    va, vb = stdev(a) ** 2, stdev(b) ** 2
    se2 = va / na + vb / nb
    if se2 <= 0.0:
        raise ValueError("zero variance in both groups — Welch t is undefined")
    t = (mean(a) - mean(b)) / math.sqrt(se2)
    df = se2**2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return t, df


def cohen_d(a: Iterable[float], b: Iterable[float]) -> float:
    """Pooled-SD standardised mean difference (Cohen 1988 eq. 2.5.1)."""

    a = list(a)
    b = list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        raise ValueError(f"need ≥2 samples per group; got {na}, {nb}")
    va, vb = stdev(a) ** 2, stdev(b) ** 2
    sp2 = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    if sp2 <= 0.0:
        raise ValueError("zero pooled variance — Cohen d is undefined")
    return (mean(a) - mean(b)) / math.sqrt(sp2)


def contrast(a: Iterable[float], b: Iterable[float]) -> ContrastResult:
    a = list(a)
    b = list(b)
    t, df = welch_t(a, b)
    d = cohen_d(a, b)
    return ContrastResult(
        n_a=len(a),
        n_b=len(b),
        mean_a=mean(a),
        mean_b=mean(b),
        std_a=stdev(a),
        std_b=stdev(b),
        welch_t=t,
        welch_df=df,
        cohen_d=d,
    )


def contrast_panel(
    a: Mapping[str, Iterable[float]],
    b: Mapping[str, Iterable[float]],
) -> dict[str, ContrastResult]:
    """Contrast each shared metric in ``a`` and ``b``."""

    metrics = sorted(set(a) & set(b))
    if not metrics:
        raise ValueError("no shared metrics between groups")
    return {m: contrast(a[m], b[m]) for m in metrics}
