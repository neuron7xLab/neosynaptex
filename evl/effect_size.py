"""Phase contrast effect sizes -- Cohen's d and ratio metrics.

Raw numbers are insufficient for PRR. Need standardized effect sizes
with confidence intervals to compare perturbation impact.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np


def cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Cohen's d: standardized mean difference.

    d = (mean_a - mean_b) / pooled_std
    Negative d means group_b has higher values.

    Interpretation:
        |d| < 0.2:  negligible
        |d| < 0.5:  small
        |d| < 0.8:  medium
        |d| >= 0.8: large
    """
    a = np.asarray(group_a, dtype=np.float64)
    b = np.asarray(group_b, dtype=np.float64)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    pooled_var = ((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2)
    pooled_std = np.sqrt(pooled_var)
    if pooled_std < 1e-15:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled_std)


def phase_contrast_effect(
    baseline_latency: np.ndarray,
    stress_latency: np.ndarray,
) -> dict:
    """Compute full effect size report for baseline vs stress phase.

    Returns:
        cohens_d:       standardized effect
        lat_ratio:      stress_mean / baseline_mean
        acc_drop_pct:   not computed here (needs accuracy arrays)
        interpretation: "negligible" | "small" | "medium" | "large"
    """
    bl = np.asarray(baseline_latency, dtype=np.float64)
    st = np.asarray(stress_latency, dtype=np.float64)

    d = cohens_d(bl, st)
    ratio = float(np.mean(st) / np.mean(bl)) if np.mean(bl) > 0 else float("nan")

    abs_d = abs(d)
    if abs_d < 0.2:
        interp = "negligible"
    elif abs_d < 0.5:
        interp = "small"
    elif abs_d < 0.8:
        interp = "medium"
    else:
        interp = "large"

    return {
        "cohens_d": round(d, 4),
        "lat_ratio": round(ratio, 4),
        "baseline_mean_ms": round(float(np.mean(bl)), 1),
        "stress_mean_ms": round(float(np.mean(st)), 1),
        "baseline_n": len(bl),
        "stress_n": len(st),
        "interpretation": interp,
    }
