"""Two-cohort contrast — Welch's t + Mann-Whitney U + Cohen d with CI.

This module is the HRV-facing facade over :mod:`tools.stats`. It
packages one parametric test (Welch's t), its non-parametric sibling
(Mann-Whitney U), the Cohen d effect size with a 95 % analytical CI,
Cliff's δ as a non-parametric effect size, and a panel-level
Benjamini-Hochberg FDR correction so a caller sweeping many metrics
does not silently inflate the family-wise error rate.

Everything is pure-Python once you get past the CDF calls inside
:mod:`tools.stats`, which in turn delegate to ``scipy.stats`` for
canonical distribution functions.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping
from statistics import mean, stdev

from tools.stats.effect_size import cliffs_delta as _cliffs_delta
from tools.stats.effect_size import cohen_d as _cohen_d_ci
from tools.stats.multiple_testing import benjamini_hochberg
from tools.stats.tests import mann_whitney_u as _mwu
from tools.stats.tests import welch_t_test as _welch

__all__ = [
    "ContrastResult",
    "PanelContrast",
    "contrast",
    "contrast_panel",
    "panel_with_fdr",
]


@dataclasses.dataclass(frozen=True)
class ContrastResult:
    """One metric, two groups — full Welch / MWU / Cohen d / Cliff's δ summary."""

    n_a: int
    n_b: int
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float
    welch_t: float
    welch_df: float
    welch_p: float
    mwu_u: float
    mwu_p: float
    cohen_d: float
    cohen_d_ci_low: float
    cohen_d_ci_high: float
    cliffs_delta: float
    cliffs_delta_ci_low: float
    cliffs_delta_ci_high: float

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
            "welch_p": _round_p(self.welch_p),
            "mwu_u": round(self.mwu_u, 2),
            "mwu_p": _round_p(self.mwu_p),
            "cohen_d": round(self.cohen_d, 3),
            "cohen_d_ci95": [
                round(self.cohen_d_ci_low, 3),
                round(self.cohen_d_ci_high, 3),
            ],
            "cliffs_delta": round(self.cliffs_delta, 3),
            "cliffs_delta_ci95": [
                round(self.cliffs_delta_ci_low, 3),
                round(self.cliffs_delta_ci_high, 3),
            ],
        }


@dataclasses.dataclass(frozen=True)
class PanelContrast:
    """A single metric's contrast plus its FDR-adjusted q-values."""

    metric: str
    contrast: ContrastResult
    welch_q_bh: float  # BH-adjusted p for Welch's t across the panel
    mwu_q_bh: float  # BH-adjusted p for Mann-Whitney U across the panel


def _round_p(p: float) -> float:
    if p != p:  # NaN
        return p
    if p < 1e-4:
        return float(f"{p:.2e}")
    return round(p, 4)


# ---------------------------------------------------------------------------
# One-metric contrast
# ---------------------------------------------------------------------------
def contrast(a: Iterable[float], b: Iterable[float]) -> ContrastResult:
    """Compute the full two-group contrast for a single metric."""

    a = list(a)
    b = list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        raise ValueError(f"need ≥2 per group; got {na}, {nb}")

    welch = _welch(a, b)
    mwu = _mwu(a, b)
    d = _cohen_d_ci(a, b)
    delta = _cliffs_delta(a, b)

    return ContrastResult(
        n_a=na,
        n_b=nb,
        mean_a=mean(a),
        mean_b=mean(b),
        std_a=stdev(a),
        std_b=stdev(b),
        welch_t=welch.statistic,
        welch_df=float(welch.df) if welch.df is not None else float("nan"),
        welch_p=welch.p_value,
        mwu_u=mwu.statistic,
        mwu_p=mwu.p_value,
        cohen_d=d.point,
        cohen_d_ci_low=d.ci_low,
        cohen_d_ci_high=d.ci_high,
        cliffs_delta=delta.point,
        cliffs_delta_ci_low=delta.ci_low,
        cliffs_delta_ci_high=delta.ci_high,
    )


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
def contrast_panel(
    a: Mapping[str, Iterable[float]],
    b: Mapping[str, Iterable[float]],
) -> dict[str, ContrastResult]:
    """Contrast each shared metric in ``a`` and ``b`` (no FDR correction)."""

    metrics = sorted(set(a) & set(b))
    if not metrics:
        raise ValueError("no shared metrics between groups")
    return {m: contrast(a[m], b[m]) for m in metrics}


def panel_with_fdr(
    a: Mapping[str, Iterable[float]],
    b: Mapping[str, Iterable[float]],
) -> list[PanelContrast]:
    """Panel contrast + Benjamini-Hochberg FDR across the panel.

    The returned order is lexicographic on the metric name so a JSON
    diff of two commits is stable. Each entry carries its own raw
    Welch / MWU p-value *and* the BH-adjusted q-value computed across
    the whole panel — downstream code can filter on either.
    """

    raw = contrast_panel(a, b)
    metrics = list(raw.keys())  # already sorted
    welch_p = [raw[m].welch_p for m in metrics]
    mwu_p = [raw[m].mwu_p for m in metrics]
    welch_q = benjamini_hochberg(welch_p)
    mwu_q = benjamini_hochberg(mwu_p)
    return [
        PanelContrast(
            metric=m,
            contrast=raw[m],
            welch_q_bh=welch_q[i],
            mwu_q_bh=mwu_q[i],
        )
        for i, m in enumerate(metrics)
    ]
