"""Core numerical and canonical operation exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .engine import run_mycelium_simulation, run_mycelium_simulation_with_history
from .exceptions import NumericalInstabilityError, StabilityError, ValueOutOfRangeError
from .extract import extract
from .field import MyceliumField
from .fractal_growth_engine import FractalConfig, FractalGrowthEngine, FractalMetrics
from .membrane_engine import MembraneConfig, MembraneEngine, MembraneMetrics
from .nernst import compute_nernst_potential
from .reaction_diffusion_engine import (
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    ReactionDiffusionMetrics,
)
from .report import report
from .stability import compute_lyapunov_exponent, compute_stability_metrics, is_stable
from .types import SimulationConfig, SimulationResult

_OPTIONAL_ATTRS = {
    "HierarchicalKrumAggregator": "mycelium_fractal_net.core.federated",
    "aggregate_gradients_krum": "mycelium_fractal_net.core.federated",
    "STDPPlasticity": "mycelium_fractal_net.core.stdp",
    "estimate_fractal_dimension": "mycelium_fractal_net.core.fractal",
    "generate_fractal_ifs": "mycelium_fractal_net.core.fractal",
    "simulate_mycelium_field": "mycelium_fractal_net.core.turing",
    # Choice Operator A_C (lazy: imports thermodynamic kernel)
    "choice_operator": "mycelium_fractal_net.core.choice_operator",
    "ChoiceResult": "mycelium_fractal_net.core.choice_operator",
    "detect_indeterminacy": "mycelium_fractal_net.core.choice_operator",
}


def __getattr__(name: str) -> Any:
    if name in _OPTIONAL_ATTRS:
        module = import_module(_OPTIONAL_ATTRS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(name)


__all__ = [
    "ChoiceResult",
    "FractalConfig",
    "FractalGrowthEngine",
    "FractalMetrics",
    "HierarchicalKrumAggregator",
    "MembraneConfig",
    "MembraneEngine",
    "MembraneMetrics",
    "MyceliumField",
    "NumericalInstabilityError",
    "ReactionDiffusionConfig",
    "ReactionDiffusionEngine",
    "ReactionDiffusionMetrics",
    "STDPPlasticity",
    "SimulationConfig",
    "SimulationResult",
    "StabilityError",
    "ValueOutOfRangeError",
    "aggregate_gradients_krum",
    "choice_operator",
    "compute_lyapunov_exponent",
    "compute_nernst_potential",
    "compute_stability_metrics",
    "detect_indeterminacy",
    "estimate_fractal_dimension",
    "extract",
    "generate_fractal_ifs",
    "is_stable",
    "report",
    "run_mycelium_simulation",
    "run_mycelium_simulation_with_history",
    "simulate_mycelium_field",
]
