"""Morphology comparison with topology drift analysis.

Comparison thresholds loaded from ``configs/detection_thresholds_v1.json``
via ``detection_config.py``. Hardcoded fallbacks ensure import-time safety.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.analytics.drift import morphology_drift
from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.detection_config import (
    CONNECTIVITY_FLAT_CEILING as _CONNECTIVITY_FLAT_CEILING,
)
from mycelium_fractal_net.core.detection_config import (
    CONNECTIVITY_LOW as _CONNECTIVITY_LOW,
)
from mycelium_fractal_net.core.detection_config import (
    CONNECTIVITY_REORG_THRESHOLD as _CONNECTIVITY_REORG_THRESHOLD,
)
from mycelium_fractal_net.core.detection_config import (
    COSINE_NEAR_IDENTICAL as _COSINE_NEAR_IDENTICAL,
)
from mycelium_fractal_net.core.detection_config import (
    COSINE_RELATED as _COSINE_RELATED,
)
from mycelium_fractal_net.core.detection_config import (
    COSINE_SIMILAR as _COSINE_SIMILAR,
)
from mycelium_fractal_net.core.detection_config import (
    DISTANCE_NEAR_IDENTICAL as _DISTANCE_NEAR_IDENTICAL,
)
from mycelium_fractal_net.core.detection_config import (
    HIERARCHY_FLAT_THRESHOLD as _HIERARCHY_FLAT_THRESHOLD,
)
from mycelium_fractal_net.core.detection_config import (
    MODULARITY_LOW as _MODULARITY_LOW,
)
from mycelium_fractal_net.core.detection_config import (
    MODULARITY_REORG_THRESHOLD as _MODULARITY_REORG_THRESHOLD,
)
from mycelium_fractal_net.core.detection_config import (
    NOISE_PATHOLOGICAL_HIGH as _NOISE_PATHOLOGICAL_HIGH,
)
from mycelium_fractal_net.core.detection_config import (
    NOISE_PATHOLOGICAL_LOW as _NOISE_PATHOLOGICAL_LOW,
)
from mycelium_fractal_net.core.detection_config import (
    TOP_CHANGED_FEATURES as _TOP_CHANGED_FEATURES,
)
from mycelium_fractal_net.types.features import MorphologyDescriptor
from mycelium_fractal_net.types.forecast import ComparisonResult

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence



__all__ = ['compare']

def _topology_label(drift: dict[str, float]) -> str:
    connectivity = float(drift.get("connectivity_divergence", 0.0))
    hierarchy = float(drift.get("hierarchy_flattening", 0.0))
    modularity = float(drift.get("modularity_shift", 0.0))
    noise = float(drift.get("noise_discrimination", 0.0))
    if noise >= _NOISE_PATHOLOGICAL_HIGH or (
        noise >= _NOISE_PATHOLOGICAL_LOW
        and connectivity < _CONNECTIVITY_LOW
        and modularity < _MODULARITY_LOW
    ):
        return "pathological-drift"
    if (
        hierarchy >= _HIERARCHY_FLAT_THRESHOLD
        and connectivity < _CONNECTIVITY_FLAT_CEILING
        and modularity < _MODULARITY_LOW
    ):
        return "flattened-hierarchy"
    if connectivity >= _CONNECTIVITY_REORG_THRESHOLD or modularity >= _MODULARITY_REORG_THRESHOLD:
        return "reorganized"
    return "nominal"


_REORGANIZATION_MAP = {
    "nominal": "stable",
    "flattened-hierarchy": "transitional",
    "pathological-drift": "pathological_noise",
    "reorganized": "reorganized",
}


def compare(
    a: FieldSequence | MorphologyDescriptor, b: FieldSequence | MorphologyDescriptor
) -> ComparisonResult:
    left = a if isinstance(a, MorphologyDescriptor) else compute_morphology_descriptor(a)
    right = b if isinstance(b, MorphologyDescriptor) else compute_morphology_descriptor(b)
    left_vec = left.to_embedding_array()
    right_vec = right.to_embedding_array()
    distance = float(np.linalg.norm(left_vec - right_vec))
    denom = float(np.linalg.norm(left_vec) * np.linalg.norm(right_vec))
    cosine = float(np.dot(left_vec, right_vec) / denom) if denom > 0 else 1.0
    left_flat = left.flatten()
    right_flat = right.flatten()
    keys = sorted(set(left_flat) & set(right_flat))
    changed = [
        {
            "feature": key,
            "left": float(left_flat[key]),
            "right": float(right_flat[key]),
            "abs_delta": abs(float(left_flat[key]) - float(right_flat[key])),
        }
        for key in sorted(keys, key=lambda k: abs(left_flat[k] - right_flat[k]), reverse=True)[
            :_TOP_CHANGED_FEATURES
        ]
    ]
    drift = morphology_drift(left, right)
    drift.update(
        {
            "connectivity_divergence": abs(
                float(
                    left.connectivity.get("connectivity_divergence", 0.0)
                    - right.connectivity.get("connectivity_divergence", 0.0)
                )
            ),
            "hierarchy_flattening": abs(
                float(
                    left.connectivity.get("hierarchy_flattening", 0.0)
                    - right.connectivity.get("hierarchy_flattening", 0.0)
                )
            ),
            "modularity_shift": abs(
                float(
                    left.connectivity.get("modularity_proxy", 0.0)
                    - right.connectivity.get("modularity_proxy", 0.0)
                )
            ),
            "noise_discrimination": abs(
                float(
                    left.neuromodulation.get("observation_noise_gain", 0.0)
                    - right.neuromodulation.get("observation_noise_gain", 0.0)
                )
            ),
        }
    )
    if cosine >= _COSINE_NEAR_IDENTICAL and distance < _DISTANCE_NEAR_IDENTICAL:
        label = "near-identical"
    elif cosine >= _COSINE_SIMILAR:
        label = "similar"
    elif cosine >= _COSINE_RELATED:
        label = "related"
    else:
        label = "divergent"
    nearest_structural_analog = (
        "self-similar"
        if label == "near-identical"
        else ("reference-family" if label in {"similar", "related"} else "no-close-analog")
    )
    topo_label = _topology_label(drift)
    reorg_label = _REORGANIZATION_MAP.get(topo_label, topo_label)
    topology_summary = {
        k: float(drift[k])
        for k in (
            "connectivity_divergence",
            "hierarchy_flattening",
            "modularity_shift",
            "noise_discrimination",
        )
    }
    return ComparisonResult(
        version="mfn-compare-v4",
        distance=distance,
        cosine_similarity=cosine,
        label=label,
        nearest_structural_analog=nearest_structural_analog,
        changed_dimensions=changed,
        drift_summary=drift,
        topology_summary=topology_summary,
        topology_label=topo_label,
        reorganization_label=reorg_label,
        metadata={
            "embedding_dim": float(len(left_vec)),
            "normalized_distance": float(drift["normalized_distance"]),
            "label_axes_orthogonal": True,
        },
    )
