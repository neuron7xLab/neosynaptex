"""Canonical feature and morphology descriptor types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import pandas as pd
    from numpy.typing import NDArray

from mycelium_fractal_net.analytics.legacy_features import (
    FEATURE_COUNT,
    FeatureVector,
    compute_features,
    validate_feature_ranges,
)

FEATURE_NAMES: list[str] = [
    "D_box",
    "D_r2",
    "V_min",
    "V_max",
    "V_mean",
    "V_std",
    "V_skew",
    "V_kurt",
    "dV_mean",
    "dV_max",
    "T_stable",
    "E_trend",
    "f_active",
    "N_clusters_low",
    "N_clusters_med",
    "N_clusters_high",
    "max_cluster_size",
    "cluster_size_std",
]

if len(FEATURE_NAMES) != FEATURE_COUNT:
    raise ValueError(
        f"FEATURE_NAMES has {len(FEATURE_NAMES)} entries but FEATURE_COUNT is {FEATURE_COUNT}"
    )

# Canonical key sets for each feature group.
# Unknown keys cause a warning (not an error) for forward compatibility.
FEATURE_NAMES_SET: frozenset[str] = frozenset(FEATURE_NAMES)

STABILITY_KEYS: frozenset[str] = frozenset(
    {
        "instability_index",
        "near_transition_score",
        "collapse_risk_score",
    }
)

COMPLEXITY_KEYS: frozenset[str] = frozenset(
    {
        "temporal_lzc",
        "temporal_hfd",
        "multiscale_entropy_short",
    }
)

CONNECTIVITY_KEYS: frozenset[str] = frozenset(
    {
        "connectivity_divergence",
        "hierarchy_flattening",
        "modularity_proxy",
        "modularity_shift",
        "global_coherence_shift",
        "active_ratio",
        "gbc_like_summary",
    }
)

NEUROMODULATION_KEYS: frozenset[str] = frozenset(
    {
        "enabled",
        "plasticity_index",
        "effective_inhibition",
        "effective_gain",
        "observation_noise_gain",
    }
)


def _validate_feature_keys(
    group_name: str,
    data: dict[str, float],
    expected: frozenset[str],
) -> None:
    """Validate feature dict keys against canonical set. Warns on unknown keys."""
    import warnings

    unknown = set(data.keys()) - expected
    if unknown:
        warnings.warn(
            f"MorphologyDescriptor.{group_name} has unknown keys: {sorted(unknown)}. "
            f"Expected subset of {sorted(expected)}.",
            stacklevel=4,
        )


@dataclass(frozen=True)
class MorphologyDescriptor:
    """Versioned morphology-aware descriptor with explainable feature groups.

    Feature groups accept both typed dataclasses and plain dicts.
    Typed access is preferred; dict interface preserved for backward compat.
    """

    version: str
    embedding: tuple[float, ...]
    features: dict[str, float] = field(default_factory=dict)
    temporal: dict[str, float] = field(default_factory=dict)
    multiscale: dict[str, float] = field(default_factory=dict)
    stability: dict[str, float] = field(default_factory=dict)
    complexity: dict[str, float] = field(default_factory=dict)
    connectivity: dict[str, float] = field(default_factory=dict)
    neuromodulation: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        d_box = self.features.get("D_box", 0.0)
        ii = self.stability.get("instability_index", 0.0)
        dims = len(self.embedding)
        return (
            f"MorphologyDescriptor(v={self.version}, "
            f"D_box={d_box:.3f}, instability={ii:.3f}, {dims} dims)"
        )

    def __post_init__(self) -> None:
        # Normalize: if typed object passed, convert to dict for storage
        for group_name in (
            "features",
            "temporal",
            "multiscale",
            "stability",
            "complexity",
            "connectivity",
            "neuromodulation",
        ):
            val = getattr(self, group_name)
            if hasattr(val, "to_dict") and not isinstance(val, dict):
                object.__setattr__(self, group_name, val.to_dict())
            else:
                object.__setattr__(self, group_name, {k: float(v) for k, v in val.items()})
        object.__setattr__(self, "embedding", tuple(float(v) for v in self.embedding))
        object.__setattr__(self, "metadata", dict(self.metadata))
        if not self.embedding:
            raise ValueError("embedding must not be empty")
        arr = np.asarray(self.embedding, dtype=np.float64)
        if not np.isfinite(arr).all():
            raise ValueError("embedding contains NaN or Inf values")
        if self.stability:
            _validate_feature_keys("stability", self.stability, STABILITY_KEYS)
        if self.complexity:
            _validate_feature_keys("complexity", self.complexity, COMPLEXITY_KEYS)
        if self.connectivity:
            _validate_feature_keys("connectivity", self.connectivity, CONNECTIVITY_KEYS)
        if self.neuromodulation:
            _validate_feature_keys("neuromodulation", self.neuromodulation, NEUROMODULATION_KEYS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "mfn-morphology-descriptor-v2",
            "descriptor_version": self.version,
            "runtime_version": "0.1.0",
            "version": self.version,
            "embedding": list(self.embedding),
            "features": dict(self.features),
            "temporal": dict(self.temporal),
            "multiscale": dict(self.multiscale),
            "stability": dict(self.stability),
            "complexity": dict(self.complexity),
            "connectivity": dict(self.connectivity),
            "neuromodulation": dict(self.neuromodulation),
            "metadata": dict(self.metadata),
        }

    def to_series(self) -> pd.Series:
        import pandas as pd

        payload = self.flatten()
        return pd.Series(payload)

    def summary(self) -> str:
        """Single-line descriptor summary."""
        n_feat = len(self.embedding)
        inst = self.stability.get("instability_index", 0.0)
        dbox = self.features.get("D_box", 0.0)
        return (
            f"[DESC] {n_feat} features | D_box={dbox:.2f} instability={inst:.3f} v={self.version}"
        )

    def flatten(self) -> dict[str, float]:
        payload: dict[str, float] = {}
        payload.update(self.features)
        payload.update({f"temporal_{k}": v for k, v in self.temporal.items()})
        payload.update({f"multiscale_{k}": v for k, v in self.multiscale.items()})
        payload.update({f"stability_{k}": v for k, v in self.stability.items()})
        payload.update({f"complexity_{k}": v for k, v in self.complexity.items()})
        payload.update({f"connectivity_{k}": v for k, v in self.connectivity.items()})
        payload.update({f"neuromodulation_{k}": v for k, v in self.neuromodulation.items()})
        payload.update({f"embedding_{i:02d}": v for i, v in enumerate(self.embedding)})
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MorphologyDescriptor:
        return cls(
            version=str(data.get("descriptor_version", data["version"])),
            embedding=tuple(float(v) for v in data["embedding"]),
            features=dict(data.get("features", {})),
            temporal=dict(data.get("temporal", {})),
            multiscale=dict(data.get("multiscale", {})),
            stability=dict(data.get("stability", {})),
            complexity=dict(data.get("complexity", {})),
            connectivity=dict(data.get("connectivity", {})),
            neuromodulation=dict(data.get("neuromodulation", {})),
            metadata=dict(data.get("metadata", {})),
        )

    def to_embedding_array(self) -> NDArray[np.float64]:
        return np.asarray(self.embedding, dtype=np.float64)

    def to_parquet_row(self) -> dict[str, float | str]:
        row: dict[str, float | str] = {"version": self.version}
        row.update(self.flatten())
        return row


__all__ = [
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "FeatureVector",
    "MorphologyDescriptor",
    "compute_features",
    "validate_feature_ranges",
]
