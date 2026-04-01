"""
Analytics submodule for MyceliumFractalNet.

Provides feature extraction and analysis utilities for fractal analysis.

Main API:
- compute_fractal_features(result: SimulationResult) -> FeatureVector
- compute_box_counting_dimension(field, ...) -> float
- compute_basic_stats(field) -> Dict[str, float]

Reference: docs/MFN_FEATURE_SCHEMA.md
"""

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from .fractal_features import (
    FeatureVector,
    compute_basic_stats,
    compute_box_counting_dimension,
    compute_fractal_features,
)
from .insight_architect import FractalInsightArchitect, Insight, InsufficientDataError

# Legacy type alias for compatibility
FeatureArray = NDArray[np.float64]
"""Type alias for 18-element feature array (see MFN_FEATURE_SCHEMA.md)."""

# ── Mathematical Frontier (v4.4.0+) ──────────────────────────────────────────
from .causal_emergence import (
    CausalEmergenceResult,
    compute_causal_emergence,
    discretize_field_pca,
    effective_information,
)
from .fisher_information import FIMResult, compute_fim, natural_gradient_step
from .fractal_arsenal import (
    BasinFractalityResult,
    FractalArsenalReport,
    LacunarityProfile,
    MultifractalSpectrum,
    compute_basin_fractality,
    compute_dlambda_dt,
    compute_fractal_arsenal,
    compute_lacunarity,
    compute_multifractal_spectrum,
    finite_size_scaling_study,
)
from .invariant_operator import (
    InvariantOperator,
    MState,
    MTrajectory,
    NullMode,
    StabilityMap,
)
from .math_frontier import MathFrontierReport, run_math_frontier
from .rmt_spectral import RMTDiagnostics, rmt_diagnostics
from .tda_ews import TopologicalSignature, compute_tda, tda_ews_trajectory
from .unified_score import (
    HWIComponents,
    UnifiedScore,
    compute_hwi_components,
    compute_unified_score,
    hwi_trajectory,
)
from .wasserstein_geometry import (
    ot_basin_stability,
    wasserstein_distance,
    wasserstein_trajectory_speed,
)

__all__ = [
    "BasinFractalityResult",
    "CausalEmergenceResult",
    "FIMResult",
    "FeatureArray",
    "FeatureVector",
    "FractalArsenalReport",
    "FractalInsightArchitect",
    "HWIComponents",
    "Insight",
    "InsufficientDataError",
    "InvariantOperator",
    "LacunarityProfile",
    "MState",
    "MTrajectory",
    "MathFrontierReport",
    "MultifractalSpectrum",
    "NullMode",
    "RMTDiagnostics",
    "StabilityMap",
    "TopologicalSignature",
    "UnifiedScore",
    "compute_basic_stats",
    "compute_basin_fractality",
    "compute_box_counting_dimension",
    "compute_causal_emergence",
    "compute_dlambda_dt",
    "compute_fim",
    "compute_fractal_arsenal",
    "compute_fractal_features",
    "compute_hwi_components",
    "compute_lacunarity",
    "compute_multifractal_spectrum",
    "compute_tda",
    "compute_unified_score",
    "discretize_field_pca",
    "effective_information",
    "finite_size_scaling_study",
    "hwi_trajectory",
    "natural_gradient_step",
    "ot_basin_stability",
    "rmt_diagnostics",
    "run_math_frontier",
    "tda_ews_trajectory",
    "wasserstein_distance",
    "wasserstein_trajectory_speed",
]
