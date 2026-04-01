"""
Core Metrics for Hippocampal CA1-LAM Memory Module.

This module provides metrics to measure memory subsystem behavior:
- Memory capacity proxy
- Recall accuracy proxy
- State drift metric
- Stability metric
- Comprehensive compute_report function

All metrics return structured dictionaries with consistent keys.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


def memory_capacity_proxy(
    weights: np.ndarray,
    method: str = "rank",
) -> float:
    """
    Compute a proxy for memory capacity.

    Methods:
    - "rank": Uses matrix rank / N as capacity proxy
    - "eigenvalue": Uses number of significant eigenvalues
    - "sparsity": Uses sparsity-based capacity estimate

    Args:
        weights: [N, N] weight matrix
        method: Capacity estimation method

    Returns:
        Capacity proxy value (normalized to [0, 1])
    """
    n = weights.shape[0]
    if n == 0:
        return 0.0

    if method == "rank":
        # Effective rank via singular values
        singular_values = np.linalg.svd(weights, compute_uv=False)
        # Normalize to get effective rank
        if singular_values.max() > 0:
            normalized = singular_values / singular_values.max()
            effective_rank = np.sum(normalized > 0.01)
            return float(effective_rank / n)
        return 0.0

    elif method == "eigenvalue":
        # Count significant eigenvalues
        eigenvalues = np.linalg.eigvals(weights)
        significant = np.sum(np.abs(eigenvalues) > 1e-6)
        return float(significant / n)

    elif method == "sparsity":
        # Hopfield-like capacity: ~0.14 * N for sparse patterns
        # Here we estimate based on connection density
        density = np.mean(np.abs(weights) > 1e-6)
        return float(density * 0.14)

    else:
        raise ValueError(f"Unknown method: {method}")


def recall_accuracy_proxy(
    original: np.ndarray,
    recalled: np.ndarray,
    method: str = "cosine",
) -> float:
    """
    Compute recall accuracy between original and recalled patterns.

    Methods:
    - "cosine": Cosine similarity
    - "correlation": Pearson correlation
    - "overlap": Fraction of matching signs (for bipolar patterns)
    - "mse": 1 - normalized MSE

    Args:
        original: [N] original pattern
        recalled: [N] recalled pattern
        method: Accuracy computation method

    Returns:
        Accuracy value in [0, 1] (or [-1, 1] for correlation)
    """
    if original.shape != recalled.shape:
        raise ValueError(f"Shape mismatch: original {original.shape} vs recalled {recalled.shape}")

    if method == "cosine":
        norm_orig = np.linalg.norm(original)
        norm_rec = np.linalg.norm(recalled)
        if norm_orig < 1e-10 or norm_rec < 1e-10:
            return 0.0
        cosine = np.dot(original, recalled) / (norm_orig * norm_rec)
        return float((cosine + 1) / 2)  # Map [-1, 1] to [0, 1]

    elif method == "correlation":
        if np.std(original) < 1e-10 or np.std(recalled) < 1e-10:
            return 0.0
        return float(np.corrcoef(original, recalled)[0, 1])

    elif method == "overlap":
        # For bipolar patterns
        return float(np.mean(np.sign(original) == np.sign(recalled)))

    elif method == "mse":
        mse = np.mean((original - recalled) ** 2)
        max_val = max(np.max(np.abs(original)), np.max(np.abs(recalled)), 1.0)
        normalized_mse = mse / (max_val**2)
        return float(1.0 - min(normalized_mse, 1.0))

    else:
        raise ValueError(f"Unknown method: {method}")


def drift_metric(
    state_before: np.ndarray,
    state_after: np.ndarray,
    method: str = "relative",
) -> float:
    """
    Compute state drift between two states.

    Methods:
    - "absolute": Mean absolute change
    - "relative": Relative change normalized by initial magnitude
    - "max": Maximum element change

    Args:
        state_before: State before operation
        state_after: State after operation
        method: Drift computation method

    Returns:
        Drift value (non-negative)
    """
    if state_before.shape != state_after.shape:
        raise ValueError(f"Shape mismatch: {state_before.shape} vs {state_after.shape}")

    diff = state_after - state_before

    if method == "absolute":
        return float(np.mean(np.abs(diff)))

    elif method == "relative":
        magnitude = np.mean(np.abs(state_before)) + 1e-10
        return float(np.mean(np.abs(diff)) / magnitude)

    elif method == "max":
        return float(np.max(np.abs(diff)))

    else:
        raise ValueError(f"Unknown method: {method}")


def stability_metric(
    weights: np.ndarray,
    method: str = "spectral",
) -> float:
    """
    Compute stability metric for weight matrix.

    Methods:
    - "spectral": Based on spectral radius (lower is more stable)
    - "condition": Based on condition number
    - "norm": Based on Frobenius norm

    Args:
        weights: [N, N] weight matrix
        method: Stability computation method

    Returns:
        Stability value (higher = more stable, normalized to [0, 1])
    """
    if method == "spectral":
        eigenvalues = np.linalg.eigvals(weights)
        rho = np.max(np.abs(eigenvalues))
        # Map spectral radius to stability: rho=0 -> 1.0, rho=1 -> 0.5, rho>1 -> <0.5
        return float(1.0 / (1.0 + rho))

    elif method == "condition":
        # Condition number-based stability
        # Infinite condition number indicates singular/ill-conditioned matrix
        cond = np.linalg.cond(weights)
        if not np.isfinite(cond):
            # Return very small positive value for numerically unstable matrices
            return 1e-10
        # Map to [0, 1]: cond=1 -> 1.0, cond=inf -> 0.0
        return float(1.0 / (1.0 + np.log1p(cond)))

    elif method == "norm":
        norm = np.linalg.norm(weights, ord="fro")
        n = weights.shape[0]
        normalized = norm / np.sqrt(n * n)  # Normalize by matrix size
        return float(1.0 / (1.0 + normalized))

    else:
        raise ValueError(f"Unknown method: {method}")


def compute_weight_statistics(weights: np.ndarray) -> Dict[str, float]:
    """
    Compute comprehensive weight matrix statistics.

    Args:
        weights: [N, N] weight matrix

    Returns:
        Dictionary of statistics
    """
    eigenvalues = np.linalg.eigvals(weights)

    return {
        "mean": float(np.mean(weights)),
        "std": float(np.std(weights)),
        "min": float(np.min(weights)),
        "max": float(np.max(weights)),
        "sparsity": float(np.mean(np.abs(weights) < 1e-6)),
        "spectral_radius": float(np.max(np.abs(eigenvalues))),
        "frobenius_norm": float(np.linalg.norm(weights, ord="fro")),
        "diagonal_mean": float(np.mean(np.diag(weights))),
    }


def compute_activation_statistics(activations: np.ndarray) -> Dict[str, float]:
    """
    Compute comprehensive activation statistics.

    Args:
        activations: [N] or [T, N] activation array

    Returns:
        Dictionary of statistics
    """
    return {
        "mean": float(np.mean(activations)),
        "std": float(np.std(activations)),
        "min": float(np.min(activations)),
        "max": float(np.max(activations)),
        "sparsity": float(np.mean(np.abs(activations) < 1e-6)),
        "l2_norm": float(np.linalg.norm(activations.flatten())),
    }


def compute_report(
    weights: np.ndarray,
    activations: np.ndarray,
    recalled_pattern: Optional[np.ndarray] = None,
    original_pattern: Optional[np.ndarray] = None,
    previous_weights: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Compute comprehensive metrics report.

    This is the main entry point for collecting all relevant metrics
    about the memory system state.

    Args:
        weights: [N, N] weight matrix
        activations: [N] current activations
        recalled_pattern: Optional [N] recalled pattern for accuracy
        original_pattern: Optional [N] original pattern for accuracy comparison
        previous_weights: Optional [N, N] previous weights for drift calculation

    Returns:
        Dictionary with all metrics, guaranteed consistent keys
    """
    report: Dict[str, Any] = {}

    # Core metrics
    report["capacity_proxy"] = memory_capacity_proxy(weights, method="rank")
    report["stability"] = stability_metric(weights, method="spectral")

    # Weight statistics
    report["weight_stats"] = compute_weight_statistics(weights)

    # Activation statistics
    report["activation_stats"] = compute_activation_statistics(activations)

    # Recall accuracy (if patterns provided)
    if recalled_pattern is not None and original_pattern is not None:
        report["recall_accuracy_cosine"] = recall_accuracy_proxy(
            original_pattern, recalled_pattern, method="cosine"
        )
        report["recall_accuracy_overlap"] = recall_accuracy_proxy(
            original_pattern, recalled_pattern, method="overlap"
        )
    else:
        report["recall_accuracy_cosine"] = None
        report["recall_accuracy_overlap"] = None

    # Drift (if previous weights provided)
    if previous_weights is not None:
        report["weight_drift_relative"] = drift_metric(previous_weights, weights, method="relative")
        report["weight_drift_max"] = drift_metric(previous_weights, weights, method="max")
    else:
        report["weight_drift_relative"] = None
        report["weight_drift_max"] = None

    # Sanity checks
    report["finite_weights"] = bool(np.all(np.isfinite(weights)))
    report["finite_activations"] = bool(np.all(np.isfinite(activations)))
    report["spectral_radius_safe"] = bool(report["weight_stats"]["spectral_radius"] <= 1.0)

    return report


# Standard report keys for validation
REPORT_KEYS = frozenset(
    [
        "capacity_proxy",
        "stability",
        "weight_stats",
        "activation_stats",
        "recall_accuracy_cosine",
        "recall_accuracy_overlap",
        "weight_drift_relative",
        "weight_drift_max",
        "finite_weights",
        "finite_activations",
        "spectral_radius_safe",
    ]
)


def validate_report(report: Dict[str, Any]) -> bool:
    """
    Validate that a report has all expected keys.

    Args:
        report: Report dictionary from compute_report

    Returns:
        True if all keys present
    """
    return REPORT_KEYS <= set(report.keys())
