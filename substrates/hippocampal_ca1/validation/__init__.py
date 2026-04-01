"""
Validation Module for Hippocampal CA1

Implements validation gates and testing:
- Laminar structure validation
- Phase precession validation
- Fractal dimension computation
- Dynamic stability validation
- Replay validation
- Golden test suite for reproducibility
"""

from .golden_tests import (
    GOLDEN_REFERENCE,
    GOLDEN_SEED,
    set_seed,
    test_calcium_plasticity_golden,
    test_full_reproducibility,
    test_input_specific_plasticity_golden,
    test_laminar_inference_golden,
    test_network_stability_golden,
    test_theta_swr_switching_golden,
)
from .validators import (
    CA1Validator,
    compute_fractal_dimension,
    validate_dynamic_stability,
    validate_laminar_structure,
    validate_phase_precession,
    validate_replay,
)

__all__ = [
    # Validators
    "CA1Validator",
    "compute_fractal_dimension",
    "validate_dynamic_stability",
    "validate_laminar_structure",
    "validate_phase_precession",
    "validate_replay",
    # Golden tests
    "GOLDEN_REFERENCE",
    "GOLDEN_SEED",
    "set_seed",
    "test_calcium_plasticity_golden",
    "test_full_reproducibility",
    "test_input_specific_plasticity_golden",
    "test_laminar_inference_golden",
    "test_network_stability_golden",
    "test_theta_swr_switching_golden",
]
