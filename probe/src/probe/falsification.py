"""Falsification battery + null result contract.

Triple test on two gamma collections (human-AI vs LLM-only):
  * permutation test  : one-sided greater, alpha = 0.01
  * Cohen's d         : effect size
  * two-sample KS     : distributional difference

Null result contract (HARD RULE 5):
  If the LLM collection shows mean gamma < 0 (matching the existing
  experiments/lm_substrate null result gamma = -0.094, p = 0.626),
  ``null_confirmed`` is True. That IS the scientific result — never
  hidden, never re-labelled as failure.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats as _sp_stats

_DEFAULT_PERMUTATIONS: int = 10_000
_SIGNIFICANCE_ALPHA: float = 0.01


@dataclass(frozen=True)
class FalsificationResult:
    permutation_p: float
    cohens_d: float
    ks_stat: float
    ks_p: float
    n_human_ai: int
    n_llm: int
    mean_human_ai: float
    mean_llm: float
    significant: bool
    null_confirmed: bool
    notes: tuple[str, ...]


def run_falsification(
    gamma_human_ai: Sequence[float],
    gamma_llm: Sequence[float],
    *,
    n_permutations: int = _DEFAULT_PERMUTATIONS,
    seed: int = 7,
) -> FalsificationResult:
    """Run permutation + Cohen's d + KS battery on two gamma groups."""
    xa = _clean(gamma_human_ai, "gamma_human_ai")
    xb = _clean(gamma_llm, "gamma_llm")
    notes: list[str] = []
    if len(xa) < 2 or len(xb) < 2:
        raise ValueError(f"each group needs >= 2 finite samples, got {len(xa)} and {len(xb)}")

    mean_a = float(np.mean(xa))
    mean_b = float(np.mean(xb))

    # Permutation test: H1 = mean(human_ai) > mean(llm)
    perm = _sp_stats.permutation_test(
        (xa, xb),
        statistic=lambda a, b: float(np.mean(a) - np.mean(b)),
        permutation_type="independent",
        n_resamples=int(n_permutations),
        alternative="greater",
        random_state=int(seed),
    )
    permutation_p = float(perm.pvalue)

    # Cohen's d with pooled std (unbiased pooled variance).
    var_a = float(np.var(xa, ddof=1))
    var_b = float(np.var(xb, ddof=1))
    pooled = math.sqrt((var_a + var_b) / 2.0) if (var_a + var_b) > 0 else 0.0
    if pooled == 0.0:
        cohens_d = 0.0 if math.isclose(mean_a, mean_b) else float("inf")
        notes.append("pooled std == 0; Cohen's d collapsed to 0 or inf.")
    else:
        cohens_d = float((mean_a - mean_b) / pooled)

    # KS two-sample.
    ks = _sp_stats.ks_2samp(xa, xb)
    ks_stat = float(ks.statistic)
    ks_p = float(ks.pvalue)

    significant = permutation_p < _SIGNIFICANCE_ALPHA
    null_confirmed = mean_b < 0.0
    if null_confirmed:
        notes.append(
            "null_confirmed: mean_llm < 0; consistent with existing "
            "experiments/lm_substrate null result (gamma = -0.094, p = 0.626)."
        )

    return FalsificationResult(
        permutation_p=permutation_p,
        cohens_d=cohens_d,
        ks_stat=ks_stat,
        ks_p=ks_p,
        n_human_ai=len(xa),
        n_llm=len(xb),
        mean_human_ai=mean_a,
        mean_llm=mean_b,
        significant=significant,
        null_confirmed=null_confirmed,
        notes=tuple(notes),
    )


def _clean(values: Sequence[float], label: str) -> list[float]:
    out: list[float] = []
    for v in values:
        fv = float(v)
        if math.isfinite(fv):
            out.append(fv)
    if not out:
        raise ValueError(f"{label}: no finite values")
    return out
