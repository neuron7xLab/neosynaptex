"""Linear state probes — probing classifiers on MFN internal states.

Tests whether gamma status (healthy/pathological) is linearly separable
in each feature group space. If a group achieves high AUC, it contains
sufficient information for classification.

Ref: Alain & Bengio (2016) Understanding intermediate layers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from .feature_extractor import FeatureVector

__all__ = ["LinearStateProbe"]


class LinearStateProbe:
    """Linear probe on MFN feature groups."""

    def __init__(
        self,
        probe_type: Literal["logistic", "ridge"] = "logistic",
        seed: int = 42,
    ) -> None:
        self.probe_type = probe_type
        self.seed = seed

    def _get_group_features(
        self,
        fv: FeatureVector,
        group: str,
    ) -> np.ndarray:
        """Extract feature vector for a specific group."""
        if group == "all":
            return fv.to_array()
        mapping = {
            "thermodynamic": fv.thermodynamic,
            "topological": fv.topological,
            "fractal": fv.fractal,
            "causal": fv.causal,
        }
        d = mapping.get(group, {})
        return np.array(list(d.values()), dtype=np.float64) if d else np.array([0.0])

    def fit(
        self,
        feature_vectors: list[FeatureVector],
        labels: list[int],
        feature_group: Literal[
            "thermodynamic", "topological", "fractal", "causal", "all"
        ] = "all",
    ) -> dict[str, float]:
        """Train linear probe on a feature group.

        Returns accuracy, roc_auc, and feature coefficients.
        Uses simple logistic regression with 5-fold cross-validation.
        """
        X = np.array([self._get_group_features(fv, feature_group) for fv in feature_vectors])
        y = np.array(labels)

        if len(np.unique(y)) < 2 or X.shape[0] < 5:
            return {"accuracy": 0.5, "roc_auc": 0.5, "n_features": X.shape[1]}

        # Standardize
        mu = X.mean(axis=0)
        std = X.std(axis=0) + 1e-12
        X_norm = (X - mu) / std

        # Simple logistic via closed-form (ridge regression as proxy)
        # For small datasets, full sklearn is overkill; use numpy ridge
        n_folds = min(5, X.shape[0])
        fold_size = X.shape[0] // n_folds
        accuracies = []
        aucs = []

        for fold in range(n_folds):
            val_start = fold * fold_size
            val_end = val_start + fold_size
            X_val = X_norm[val_start:val_end]
            y_val = y[val_start:val_end]
            X_train = np.concatenate([X_norm[:val_start], X_norm[val_end:]])
            y_train = np.concatenate([y[:val_start], y[val_end:]])

            if len(np.unique(y_train)) < 2 or len(y_val) < 1:
                continue

            # Ridge regression
            lam = 1.0
            w = np.linalg.solve(
                X_train.T @ X_train + lam * np.eye(X_train.shape[1]),
                X_train.T @ y_train,
            )

            y_pred_val = X_val @ w
            y_pred_bin = (y_pred_val > 0.5).astype(int)
            acc = float(np.mean(y_pred_bin == y_val))
            accuracies.append(acc)

            # Simple AUC approximation
            if len(np.unique(y_val)) == 2:
                pos_scores = y_pred_val[y_val == 1]
                neg_scores = y_pred_val[y_val == 0]
                if len(pos_scores) > 0 and len(neg_scores) > 0:
                    auc = float(np.mean(
                        pos_scores[:, None] > neg_scores[None, :]
                    ))
                    aucs.append(auc)

        return {
            "accuracy": float(np.mean(accuracies)) if accuracies else 0.5,
            "roc_auc": float(np.mean(aucs)) if aucs else 0.5,
            "n_features": X.shape[1],
            "n_samples": X.shape[0],
            "feature_group": feature_group,
        }

    def probe_all_groups(
        self,
        feature_vectors: list[FeatureVector],
        labels: list[int],
    ) -> dict[str, dict[str, float]]:
        """Probe all feature groups and compare."""
        groups = ["thermodynamic", "topological", "fractal", "causal", "all"]
        return {g: self.fit(feature_vectors, labels, g) for g in groups}  # type: ignore[arg-type]
