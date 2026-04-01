"""model_pkg — decomposed model.py into bounded modules.

Re-exports all public symbols from the original model.py for backward compatibility.
The original model.py imports from here.
"""

from __future__ import annotations

from mycelium_fractal_net.model_pkg.aggregation import (
    HierarchicalKrumAggregator,
)
from mycelium_fractal_net.model_pkg.biophysics import (
    BODY_TEMPERATURE_K,
    FARADAY_CONSTANT,
    ION_CLAMP_MIN,
    NERNST_RTFZ_MV,
    QUANTUM_JITTER_VAR,
    R_GAS_CONSTANT,
    TURING_THRESHOLD,
    compute_lyapunov_exponent,
    compute_nernst_potential,
    estimate_fractal_dimension,
    generate_fractal_ifs,
    simulate_mycelium_field,
)
from mycelium_fractal_net.model_pkg.components import (
    SPARSE_TOPK,
    STDP_A_MINUS,
    STDP_A_PLUS,
    STDP_TAU_MINUS,
    STDP_TAU_PLUS,
    SparseAttention,
    STDPPlasticity,
)
from mycelium_fractal_net.model_pkg.network import (
    MyceliumFractalNet,
    ValidationConfig,
    run_validation,
    run_validation_cli,
)

__all__ = [
    "BODY_TEMPERATURE_K",
    "FARADAY_CONSTANT",
    "ION_CLAMP_MIN",
    "NERNST_RTFZ_MV",
    "QUANTUM_JITTER_VAR",
    "R_GAS_CONSTANT",
    "SPARSE_TOPK",
    "STDP_A_MINUS",
    "STDP_A_PLUS",
    "STDP_TAU_MINUS",
    "STDP_TAU_PLUS",
    "TURING_THRESHOLD",
    "HierarchicalKrumAggregator",
    "MyceliumFractalNet",
    "STDPPlasticity",
    "SparseAttention",
    "ValidationConfig",
    "compute_lyapunov_exponent",
    "compute_nernst_potential",
    "estimate_fractal_dimension",
    "generate_fractal_ifs",
    "run_validation",
    "run_validation_cli",
    "simulate_mycelium_field",
]
