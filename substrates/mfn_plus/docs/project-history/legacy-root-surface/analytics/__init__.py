"""Compatibility shim for analytics; canonical code lives under mycelium_fractal_net.analytics."""

from warnings import warn

from mycelium_fractal_net.analytics.legacy_features import (
    FEATURE_COUNT,
    FeatureConfig,
    FeatureVector,
    compute_basic_stats,
    compute_features,
    compute_fractal_features,
    compute_structural_features,
    compute_temporal_features,
)

warn(
    "Importing 'analytics' is deprecated; use 'mycelium_fractal_net.analytics' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "FEATURE_COUNT",
    "FeatureConfig",
    "FeatureVector",
    "compute_features",
    "compute_fractal_features",
    "compute_basic_stats",
    "compute_temporal_features",
    "compute_structural_features",
]
