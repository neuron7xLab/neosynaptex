"""Reaction-diffusion configuration and parameter validation.

Contains all parameter bounds, validation logic, and configuration
dataclasses for the reaction-diffusion engine.

Reference: MFN_MATH_MODEL.md Section 2 (Reaction-Diffusion Processes)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mycelium_fractal_net.neurochem.config_types import NeuromodulationConfig

from .exceptions import StabilityError, ValueOutOfRangeError

# === Default Parameters (from MFN_MATH_MODEL.md Section 2.3) ===
DEFAULT_D_ACTIVATOR: float = 0.1
DEFAULT_D_INHIBITOR: float = 0.05
DEFAULT_R_ACTIVATOR: float = 0.01
DEFAULT_R_INHIBITOR: float = 0.02
DEFAULT_TURING_THRESHOLD: float = 0.75
DEFAULT_FIELD_ALPHA: float = 0.18
DEFAULT_QUANTUM_JITTER_VAR: float = 0.0005

# === Biophysical Parameter Bounds ===
D_ACTIVATOR_MIN: float = 0.01
D_ACTIVATOR_MAX: float = 0.5
D_INHIBITOR_MIN: float = 0.01
D_INHIBITOR_MAX: float = 0.3
R_ACTIVATOR_MIN: float = 0.001
R_ACTIVATOR_MAX: float = 0.1
R_INHIBITOR_MIN: float = 0.001
R_INHIBITOR_MAX: float = 0.1
TURING_THRESHOLD_MIN: float = 0.0
TURING_THRESHOLD_MAX: float = 1.0
ALPHA_MIN: float = 0.05
ALPHA_MAX: float = 0.25
JITTER_VAR_MIN: float = 0.0
JITTER_VAR_MAX: float = 0.01
GRID_SIZE_MIN: int = 4
GRID_SIZE_MAX: int = 1024

# === STDP-like adaptive diffusivity (Bi & Poo 1998 analogy) ===
# LTP: where Turing pattern is active, strengthen diffusion
# LTD: where dormant, weaken diffusion (A-/A+ = 1.2, asymmetric for stability)
ALPHA_LTP_RATE: float = 0.001
ALPHA_LTD_RATE: float = 0.0012

# === Stability Limits ===
MAX_STABLE_DIFFUSION: float = 0.25

# === Field Bounds ===
FIELD_V_MIN: float = -0.095
FIELD_V_MAX: float = 0.040
INITIAL_POTENTIAL_MEAN: float = -0.070
INITIAL_POTENTIAL_STD: float = 0.005


class BoundaryCondition(Enum):
    """Available boundary conditions for the spatial grid."""

    PERIODIC = "periodic"
    NEUMANN = "neumann"
    DIRICHLET = "dirichlet"


def _validate_diffusion_coefficient(
    name: str,
    value: float,
    min_bound: float,
    cfl_limit: float = MAX_STABLE_DIFFUSION,
) -> None:
    if value > cfl_limit:
        raise StabilityError(
            f"{name}={value} exceeds CFL stability limit "
            f"of {cfl_limit}. Reduce to maintain numerical stability."
        )
    if value < min_bound:
        raise ValueOutOfRangeError(
            f"{name} must be in [{min_bound}, {cfl_limit})",
            value=value,
            min_bound=min_bound,
            max_bound=cfl_limit,
            parameter_name=name,
        )


@dataclass
class ReactionDiffusionConfig:
    """Configuration for reaction-diffusion engine.

    All parameters have physically meaningful defaults from MFN_MATH_MODEL.md.
    """

    grid_size: int = 64
    d_activator: float = DEFAULT_D_ACTIVATOR
    d_inhibitor: float = DEFAULT_D_INHIBITOR
    r_activator: float = DEFAULT_R_ACTIVATOR
    r_inhibitor: float = DEFAULT_R_INHIBITOR
    turing_threshold: float = DEFAULT_TURING_THRESHOLD
    alpha: float = DEFAULT_FIELD_ALPHA
    boundary_condition: BoundaryCondition = BoundaryCondition.PERIODIC
    quantum_jitter: bool = False
    jitter_var: float = DEFAULT_QUANTUM_JITTER_VAR
    spike_probability: float = 0.25
    check_stability: bool = True
    random_seed: int | None = None
    neuromodulation: NeuromodulationConfig | None = None
    accel_laplacian: bool = True
    alpha_guard_enabled: bool = True
    alpha_guard_threshold: float = 0.95
    soft_boundary_damping: float = 0.35
    adaptive_alpha: bool = True

    def __post_init__(self) -> None:
        # Accept dict for backward compatibility — convert to typed config
        if isinstance(self.neuromodulation, dict):
            object.__setattr__(
                self, "neuromodulation", NeuromodulationConfig.from_dict(self.neuromodulation)
            )
        if not (GRID_SIZE_MIN <= self.grid_size <= GRID_SIZE_MAX):
            raise ValueOutOfRangeError(
                f"Grid size must be in [{GRID_SIZE_MIN}, {GRID_SIZE_MAX}]",
                value=float(self.grid_size),
                min_bound=float(GRID_SIZE_MIN),
                max_bound=float(GRID_SIZE_MAX),
                parameter_name="grid_size",
            )
        _validate_diffusion_coefficient("d_activator", self.d_activator, D_ACTIVATOR_MIN)
        _validate_diffusion_coefficient("d_inhibitor", self.d_inhibitor, D_INHIBITOR_MIN)
        _validate_diffusion_coefficient("alpha", self.alpha, ALPHA_MIN)
        if not (R_ACTIVATOR_MIN <= self.r_activator <= R_ACTIVATOR_MAX):
            raise ValueOutOfRangeError(
                f"r_activator must be in [{R_ACTIVATOR_MIN}, {R_ACTIVATOR_MAX}]",
                value=self.r_activator,
                min_bound=R_ACTIVATOR_MIN,
                max_bound=R_ACTIVATOR_MAX,
                parameter_name="r_activator",
            )
        if not (R_INHIBITOR_MIN <= self.r_inhibitor <= R_INHIBITOR_MAX):
            raise ValueOutOfRangeError(
                f"r_inhibitor must be in [{R_INHIBITOR_MIN}, {R_INHIBITOR_MAX}]",
                value=self.r_inhibitor,
                min_bound=R_INHIBITOR_MIN,
                max_bound=R_INHIBITOR_MAX,
                parameter_name="r_inhibitor",
            )
        if not (TURING_THRESHOLD_MIN <= self.turing_threshold <= TURING_THRESHOLD_MAX):
            raise ValueOutOfRangeError(
                f"turing_threshold must be in [{TURING_THRESHOLD_MIN}, {TURING_THRESHOLD_MAX}]",
                value=self.turing_threshold,
                min_bound=TURING_THRESHOLD_MIN,
                max_bound=TURING_THRESHOLD_MAX,
                parameter_name="turing_threshold",
            )
        if not (0 <= self.spike_probability <= 1):
            raise ValueOutOfRangeError(
                "Spike probability must be in [0, 1]",
                value=self.spike_probability,
                min_bound=0.0,
                max_bound=1.0,
                parameter_name="spike_probability",
            )
        if not (JITTER_VAR_MIN <= self.jitter_var <= JITTER_VAR_MAX):
            raise ValueOutOfRangeError(
                f"jitter_var must be in [{JITTER_VAR_MIN}, {JITTER_VAR_MAX}]",
                value=self.jitter_var,
                min_bound=JITTER_VAR_MIN,
                max_bound=JITTER_VAR_MAX,
                parameter_name="jitter_var",
            )


@dataclass
class ReactionDiffusionMetrics:
    """Metrics collected during reaction-diffusion simulation."""

    field_min_v: float = 0.0
    field_max_v: float = 0.0
    field_mean_v: float = 0.0
    field_std_v: float = 0.0
    activator_mean: float = 0.0
    inhibitor_mean: float = 0.0
    steps_computed: int = 0
    growth_events: int = 0
    turing_activations: int = 0
    nan_detected: bool = False
    inf_detected: bool = False
    clamping_events: int = 0
    steps_to_instability: int | None = None
    plasticity_index_mean: float = 0.0
    effective_inhibition_mean: float = 0.0
    effective_gain_mean: float = 0.0
    observation_noise_gain_mean: float = 0.0
    occupancy_resting_mean: float = 1.0
    occupancy_active_mean: float = 0.0
    occupancy_desensitized_mean: float = 0.0
    occupancy_mass_error_max: float = 0.0
    excitability_offset_mean_v: float = 0.0
    alpha_guard_triggered: bool = False
    alpha_guard_triggers: int = 0
    substeps_used: int = 1
    effective_dt: float = 1.0
    soft_boundary_pressure: float = 0.0
    hard_clamp_events: int = 0
