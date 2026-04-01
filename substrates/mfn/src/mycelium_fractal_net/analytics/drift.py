from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.features import MorphologyDescriptor


def morphology_drift(
    reference: MorphologyDescriptor, candidate: MorphologyDescriptor
) -> dict[str, float]:
    ref = reference.to_embedding_array()
    cand = candidate.to_embedding_array()
    delta = cand - ref
    distance = float(np.linalg.norm(delta))
    mean_abs = float(np.mean(np.abs(delta)))
    max_abs = float(np.max(np.abs(delta)))
    denom = float(np.linalg.norm(ref) + 1e-12)
    normalized_distance = float(distance / denom)
    cosine_denom = float(np.linalg.norm(ref) * np.linalg.norm(cand))
    cosine_similarity = float(np.dot(ref, cand) / cosine_denom) if cosine_denom > 0 else 1.0
    drift_score = float(min(1.0, 0.65 * normalized_distance + 0.35 * (1.0 - cosine_similarity)))
    return {
        "distance": distance,
        "normalized_distance": normalized_distance,
        "mean_abs_delta": mean_abs,
        "max_abs_delta": max_abs,
        "cosine_similarity": cosine_similarity,
        "drift_score": drift_score,
    }
