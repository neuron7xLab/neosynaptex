"""
Configuration types for MyceliumFractalNet.

Provides canonical configuration dataclasses for simulation, feature extraction,
and dataset generation. All configurations validate their invariants on construction.

Reference:
    - docs/MFN_MATH_MODEL.md — Parameter bounds and physical constraints
    - docs/MFN_FEATURE_SCHEMA.md — Feature extraction configuration
    - docs/MFN_DATA_PIPELINES.md — Dataset configuration
"""

from __future__ import annotations

# Import FeatureConfig and DatasetConfig from config module
from mycelium_fractal_net.config import DatasetConfig, FeatureConfig

# Re-export existing canonical types to maintain single source of truth
# SimulationConfig and SimulationResult are the canonical types from core
from mycelium_fractal_net.core.types import SimulationConfig, SimulationResult

__all__ = [
    "DatasetConfig",
    "FeatureConfig",
    "SimulationConfig",
    "SimulationResult",
]
