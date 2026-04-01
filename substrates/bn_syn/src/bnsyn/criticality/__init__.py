"""Criticality analysis and control subpackage.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports branching estimators and sigma control utilities.

References
----------
docs/SPEC.md#P0-4
"""

from .analysis import PowerLawFit, fit_power_law_mle, mr_branching_ratio
from .branching import BranchingEstimator, SigmaController
from .phase_transition import CriticalPhase, PhaseTransition, PhaseTransitionDetector
from .renormalization import (
    RenormalizationEngine,
    RenormalizationParams,
    RenormalizationResult,
    ScaleMetrics,
)

__all__ = [
    "BranchingEstimator",
    "SigmaController",
    "PowerLawFit",
    "fit_power_law_mle",
    "mr_branching_ratio",
    "CriticalPhase",
    "PhaseTransition",
    "PhaseTransitionDetector",
    "RenormalizationEngine",
    "RenormalizationParams",
    "RenormalizationResult",
    "ScaleMetrics",
]
