"""Adaptation — S_{t+1} = U(S_t, x_t) under C constraints.

EMA update of norm space centroid and shape matrix.
Learning rate clipped to C.learning_rate_bounds.
Shape matrix contracted by C.contraction_factor.

Read-only on system state. Writes only to NormSpace (internal tau-control state).
"""

from __future__ import annotations

import numpy as np

from .types import MetaRuleSpace, NormSpace

__all__ = ["adapt_norm"]


def adapt_norm(
    norm: NormSpace,
    x: np.ndarray,
    success: bool,
    meta: MetaRuleSpace,
) -> NormSpace:
    """Update norm space from observation x under meta-rule constraints.

    Only updates centroid on success (reward signal).
    Shape matrix always updated via EMA contraction.
    Learning rate clipped to meta.learning_rate_bounds.
    """
    d = len(norm.centroid)
    lr_min, lr_max = meta.learning_rate_bounds
    gamma = meta.contraction_factor

    # Adaptive learning rate: higher when close to centroid
    dist = norm.mahalanobis(x)
    raw_lr = 0.01 / (1.0 + dist)
    eta = float(np.clip(raw_lr, lr_min, lr_max))

    # Centroid update: only on success
    if success:
        new_centroid = norm.centroid * (1.0 - eta) + x * eta
    else:
        new_centroid = norm.centroid.copy()

    # Shape matrix: EMA with contraction
    diff = (x - new_centroid).reshape(-1, 1)
    outer = diff @ diff.T
    new_shape = norm.shape_matrix * gamma + outer * (1.0 - gamma)

    # Ensure positive definiteness
    eigvals = np.linalg.eigvalsh(new_shape)
    if np.any(eigvals <= 0):
        new_shape = new_shape + np.eye(d) * (abs(float(np.min(eigvals))) + 1e-6)

    # Confidence: higher when norm is stable (low drift)
    drift = float(np.linalg.norm(new_centroid - norm.centroid))
    new_confidence = float(np.clip(norm.confidence * (1.0 - drift), 0.0, 1.0))

    return NormSpace(
        centroid=new_centroid,
        shape_matrix=new_shape,
        confidence=new_confidence,
    )
