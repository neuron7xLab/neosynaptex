"""JSON report generation for H_φγ invariant experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_substrate_entry(
    name: str,
    ratio_method: str,
    n_windows: int,
    n_unity_windows: int,
    median_ratio: float,
    mean_ratio: float,
    bootstrap_ci: tuple[float, float],
    null_median: float,
    p_value: float,
    verdict: str,
    phi: float = 1.6180339887498949,
    phi_inv: float = 0.6180339887498949,
) -> dict[str, Any]:
    """Build a single substrate entry for the JSON report."""
    return {
        "name": name,
        "ratio_method": ratio_method,
        "n_windows": int(n_windows),
        "n_unity_windows": int(n_unity_windows),
        "median_ratio": float(median_ratio),
        "mean_ratio": float(mean_ratio),
        "bootstrap_ci": [float(bootstrap_ci[0]), float(bootstrap_ci[1])],
        "distance_to_phi": float(abs(median_ratio - phi)),
        "distance_to_phi_inv": float(abs(median_ratio - phi_inv)),
        "null_median": float(null_median),
        "p_value": float(p_value),
        "verdict": verdict,
    }


def build_cross_substrate(
    substrates: list[dict[str, Any]],
    phi: float = 1.6180339887498949,
    phi_inv: float = 0.6180339887498949,
) -> dict[str, Any]:
    """Aggregate cross-substrate summary."""
    import numpy as np

    n_support = sum(1 for s in substrates if s["verdict"] == "support")
    n_reject = sum(1 for s in substrates if s["verdict"] == "reject")
    n_insufficient = sum(1 for s in substrates if s["verdict"] == "insufficient")

    medians = [s["median_ratio"] for s in substrates if s["verdict"] != "insufficient"]
    if medians:
        pooled_median = float(np.median(medians))
        # Simple percentile CI on the pooled medians
        if len(medians) >= 2:
            pooled_ci = [float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5))]
        else:
            pooled_ci = [float(medians[0]), float(medians[0])]
    else:
        pooled_median = 0.0
        pooled_ci = [0.0, 0.0]

    d_phi = abs(pooled_median - phi)
    d_phi_inv = abs(pooled_median - phi_inv)
    if pooled_median == 0.0:
        closest = "none"
    elif d_phi <= d_phi_inv:
        closest = "phi"
    else:
        closest = "phi_inv"

    return {
        "n_support": n_support,
        "n_reject": n_reject,
        "n_insufficient": n_insufficient,
        "pooled_median_ratio": pooled_median,
        "pooled_ci": pooled_ci,
        "closest_target": closest,
    }


def build_report(
    substrates: list[dict[str, Any]],
    epsilon: float = 0.10,
    window: int = 256,
    step: int = 32,
    phi: float = 1.6180339887498949,
    phi_inv: float = 0.6180339887498949,
) -> dict[str, Any]:
    """Build the full JSON report."""
    return {
        "hypothesis": "H_phi_gamma",
        "phi": phi,
        "phi_inv": phi_inv,
        "epsilon": epsilon,
        "window": window,
        "step": step,
        "substrates": substrates,
        "cross_substrate": build_cross_substrate(substrates, phi=phi, phi_inv=phi_inv),
    }


def save_report(report: dict[str, Any], path: str | Path) -> None:
    """Write the JSON report to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
