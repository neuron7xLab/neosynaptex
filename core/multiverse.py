"""432 pipeline combinations per substrate (verified: 4x3x3x2x2x3=432).

Execution order: per-substrate parallel where possible.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class MultiverseCell:
    substrate: str
    window_ratio: float
    overlap: float
    topo_summary: str
    metric: str
    estimator: str
    block_m: int
    gamma: float
    ci_low: float
    ci_high: float
    n_eff: int
    p_null: float
    ci_contains_unity: bool
    ci_excludes_zero: bool
    quality_flag: str  # "ok" | "low_range" | "few_pairs" | "low_r2"


MULTIVERSE_GRID: dict[str, list] = {
    "window_ratio": [0.5, 1.0, 2.0, 4.0],
    "overlap": [0.0, 0.5, 0.75],
    "topo_summary": ["h0_entropy", "h01_entropy", "betti_area"],
    "metric": ["euclidean", "correlation"],
    "estimator": ["theilslopes", "huber"],
    "block_m": [1, 2, 4],
}
# 4 x 3 x 3 x 2 x 2 x 3 = 432 confirmed


def multiverse_summary(cells: list[MultiverseCell]) -> dict:
    """R_plus = P(gamma > 0), R_unity = P(1 in CI_95), R_strong = combined."""
    gammas = np.array([c.gamma for c in cells if c.quality_flag == "ok"])
    if len(gammas) == 0:
        return {"error": "no valid cells"}
    return {
        "n_cells_total": len(cells),
        "n_cells_valid": len(gammas),
        "median_gamma": float(np.median(gammas)),
        "p05_gamma": float(np.percentile(gammas, 5)),
        "p95_gamma": float(np.percentile(gammas, 95)),
        "R_plus": float(np.mean(gammas > 0)),
        "R_unity": float(np.mean([c.ci_contains_unity for c in cells if c.quality_flag == "ok"])),
        "R_strong": float(
            np.mean(
                [
                    c.gamma > 0 and c.ci_contains_unity and abs(c.p_null) < 0.25
                    for c in cells
                    if c.quality_flag == "ok"
                ]
            )
        ),
    }
