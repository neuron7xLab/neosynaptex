"""Bridges to external causal discovery/inference frameworks.

DAGMA — differentiable DAG learning (NeurIPS 2022)
DoWhy — causal inference with refutation (py-why)

Usage:
    from mycelium_fractal_net.analytics.causal_bridge import (
        DagmaBridge, DoWhyBridge,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["CausalDiscoveryResult", "DagmaBridge", "DoWhyBridge"]


@dataclass
class CausalDiscoveryResult:
    """Result from causal structure discovery."""

    adjacency_matrix: np.ndarray
    n_nodes: int
    n_edges: int
    feature_names: list[str]
    method: str

    def summary(self) -> str:
        return f"[CAUSAL] {self.n_nodes} nodes, {self.n_edges} edges ({self.method})"


class DagmaBridge:
    """Bridge to DAGMA for DAG structure learning on R-D features.

    Discovers causal graph between feature channels across time.
    """

    def __init__(self, lambda1: float = 0.03, threshold: float = 0.3):
        self.lambda1 = lambda1
        self.threshold = threshold

    def discover(
        self, feature_matrix: np.ndarray, feature_names: list[str] | None = None
    ) -> CausalDiscoveryResult:
        """Discover causal DAG from time-series feature matrix.

        Args:
            feature_matrix: shape (T, n_features) — features over time
            feature_names: optional names for each feature column
        """
        try:
            from dagma.linear import DagmaLinear
        except ImportError:
            raise ImportError("dagma not installed: pip install dagma-linear") from None

        n_features = feature_matrix.shape[1]
        if feature_names is None:
            feature_names = [f"f{i}" for i in range(n_features)]

        model = DagmaLinear(loss_type="l2")
        W = model.fit(feature_matrix, lambda1=self.lambda1, w_threshold=self.threshold)

        # Threshold small weights
        W_thresh = np.where(np.abs(W) > self.threshold, W, 0.0)
        n_edges = int(np.count_nonzero(W_thresh))

        return CausalDiscoveryResult(
            adjacency_matrix=W_thresh,
            n_nodes=n_features,
            n_edges=n_edges,
            feature_names=feature_names,
            method="DAGMA-linear",
        )

    def discover_from_history(self, history: np.ndarray, stride: int = 1) -> CausalDiscoveryResult:
        """Discover causal structure from raw field history.

        Extracts spatial statistics per frame, then runs DAGMA.
        """
        T = history.shape[0]
        features = []
        names = ["mean", "std", "max", "min", "gradient_energy", "entropy"]

        for t in range(0, T, stride):
            f = history[t]
            dx = np.diff(f, axis=1)
            dy = np.diff(f, axis=0)
            grad_energy = float(np.mean(dx**2) + np.mean(dy**2))
            p = np.abs(f.ravel()) + 1e-12
            p = p / p.sum()
            entropy = float(-np.sum(p * np.log(p)))

            features.append(
                [
                    float(np.mean(f)),
                    float(np.std(f)),
                    float(np.max(f)),
                    float(np.min(f)),
                    grad_energy,
                    entropy,
                ]
            )

        return self.discover(np.array(features), names)


class DoWhyBridge:
    """Bridge to DoWhy for causal inference with refutation.

    Maps MFN's rule-based validation to DoWhy's refutation API.
    """

    def __init__(self, treatment: str = "alpha", outcome: str = "anomaly_score"):
        self.treatment = treatment
        self.outcome = outcome

    def estimate_and_refute(
        self,
        data: np.ndarray | dict[str, np.ndarray],
        treatment_col: str | None = None,
        outcome_col: str | None = None,
        refuters: list[str] | None = None,
    ) -> dict[str, Any]:
        """Estimate causal effect and refute with placebo/random causes.

        Args:
            data: dict of {column_name: values} or structured array
            refuters: list of refutation methods
        """
        try:
            from dowhy import CausalModel
        except ImportError:
            raise ImportError("dowhy not installed: pip install dowhy") from None

        pd = __import__("pandas")  # lazy — avoids static import detection

        treatment = treatment_col or self.treatment
        outcome = outcome_col or self.outcome

        if isinstance(data, np.ndarray):
            T = data.shape[0]
            df = pd.DataFrame(
                {
                    "mean": [float(np.mean(data[t])) for t in range(T)],
                    "std": [float(np.std(data[t])) for t in range(T)],
                    "max": [float(np.max(data[t])) for t in range(T)],
                    "entropy": [
                        float(
                            -np.sum(
                                np.abs(data[t].ravel() / (np.sum(np.abs(data[t])) + 1e-12))
                                * np.log(
                                    np.abs(data[t].ravel() / (np.sum(np.abs(data[t])) + 1e-12))
                                    + 1e-12
                                )
                            )
                        )
                        for t in range(T)
                    ],
                }
            )
            treatment = "mean"
            outcome = "entropy"
        else:
            df = pd.DataFrame(data)

        model = CausalModel(
            data=df,
            treatment=treatment,
            outcome=outcome,
            common_causes=[c for c in df.columns if c not in (treatment, outcome)],
        )

        identified = model.identify_effect()
        estimate = model.estimate_effect(identified, method_name="backdoor.linear_regression")

        result = {
            "estimate": float(estimate.value),
            "treatment": treatment,
            "outcome": outcome,
            "refutations": {},
        }

        if refuters is None:
            refuters = ["random_common_cause"]

        for ref_name in refuters:
            try:
                ref = model.refute_estimate(identified, estimate, method_name=ref_name)
                result["refutations"][ref_name] = {
                    "new_effect": float(ref.new_effect) if hasattr(ref, "new_effect") else None,
                    "refutation_result": str(ref.refutation_result)
                    if hasattr(ref, "refutation_result")
                    else "unknown",
                }
            except Exception as e:
                result["refutations"][ref_name] = {"error": str(e)[:100]}

        return result
