"""Statistical primitives for the γ-program and the HRV preprint.

A focused library of hypothesis tests, effect-size estimators,
multiple-testing corrections, and classifier-metric confidence
intervals. Each formula in this package is cited in the docstring of
the function that implements it, so an auditor can verify the
arithmetic without jumping to secondary literature.

Design rules
------------
1. Every returned object is a frozen dataclass with a stable
   ``as_json()`` shape. No naked tuples.
2. Every function that consumes data rejects degenerate input
   (too-small samples, zero variance) with a ``ValueError`` rather
   than emitting NaN and hoping a downstream caller checks.
3. Reference implementations (``scipy.stats``) are used where a
   textbook formula would just duplicate them (t / χ² / normal
   CDFs, Mann-Whitney U). Anything that has *choices* embedded in
   it (bootstrap variant, BH-FDR tie handling, Hanley-McNeil
   pairing) is implemented in this package and tested against a
   canonical reference.
"""

from __future__ import annotations

from tools.stats.classifier_metrics import (
    auc_with_hanley_mcneil_ci,
    bootstrap_metric_ci,
    wilson_interval,
)
from tools.stats.effect_size import (
    EffectSize,
    bootstrap_ci,
    cliffs_delta,
    cohen_d,
    hedges_g,
)
from tools.stats.multiple_testing import (
    benjamini_hochberg,
    bonferroni,
    holm_bonferroni,
)
from tools.stats.tests import (
    TestResult,
    mann_whitney_u,
    permutation_test,
    welch_t_test,
)

__all__ = [
    "EffectSize",
    "TestResult",
    "auc_with_hanley_mcneil_ci",
    "benjamini_hochberg",
    "bonferroni",
    "bootstrap_ci",
    "bootstrap_metric_ci",
    "cliffs_delta",
    "cohen_d",
    "hedges_g",
    "holm_bonferroni",
    "mann_whitney_u",
    "permutation_test",
    "welch_t_test",
    "wilson_interval",
]
