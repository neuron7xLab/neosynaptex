"""
High-level simulation engine for MyceliumFractalNet.

Provides the main entry point `run_mycelium_simulation` that runs a complete
mycelium field simulation and returns a structured SimulationResult.

This module integrates the numerical core from the ReactionDiffusionEngine
with the SimulationConfig/SimulationResult types.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import numpy as np

from .reaction_diffusion_engine import ReactionDiffusionConfig, ReactionDiffusionEngine
from .types import SimulationConfig, SimulationMetrics, SimulationResult

if TYPE_CHECKING:
    from numpy.typing import NDArray


def run_mycelium_simulation(config: SimulationConfig) -> SimulationResult:
    """
    Run a mycelium field simulation with the given configuration.

    This is the high-level API for running simulations. It initializes
    the field, runs the configured number of steps, and returns structured
    results including the final field state and optional history.

    Args:
        config: SimulationConfig with simulation parameters including:
            - grid_size: Size of the 2D grid (N × N). Range: [4, 512].
            - steps: Number of simulation steps. Range: [1, 10000].
            - alpha: Diffusion coefficient. Range: (0, 0.25] for CFL stability.
            - spike_probability: Probability of spike events per step. Range: [0, 1].
            - turing_enabled: Enable Turing morphogenesis patterns.
            - turing_threshold: Threshold for pattern activation. Range: [0, 1].
            - quantum_jitter: Enable quantum noise jitter.
            - jitter_var: Variance of quantum jitter. Range: [0, 0.01].
            - seed: Random seed for reproducibility. None for random seed.

    Returns:
        SimulationResult containing:
            - field: Final 2D potential field in Volts (N × N). No NaN/Inf values.
            - history: None (use run_mycelium_simulation_with_history for history).
            - growth_events: Total number of growth events during simulation.
            - metadata: Dict with timing, parameters, and simulation metrics.

    Raises:
        TypeError: If config is not a SimulationConfig instance.
        ValueError: If config parameters are invalid (propagated from SimulationConfig).
        StabilityError: If numerical instability is detected during simulation.

    Examples:
        >>> from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation
        >>> config = SimulationConfig(grid_size=32, steps=10, seed=42)
        >>> result = run_mycelium_simulation(config)
        >>> result.field.shape
        (32, 32)
        >>> result.grid_size
        32

    Notes:
        - The simulation uses periodic boundary conditions.
        - Field values are clamped to physiological bounds [-95 mV, +40 mV].
        - For reproducible results, always set the seed parameter.
        - Does not modify the input config object.
        - Deterministic: same config + seed produces identical results.
    """
    # Validate config type
    if not isinstance(config, SimulationConfig):
        raise TypeError(f"config must be SimulationConfig, got {type(config).__name__}")

    start_time = time.perf_counter()

    # Create RD engine configuration from SimulationConfig
    rd_config = ReactionDiffusionConfig(
        grid_size=config.grid_size,
        alpha=config.alpha,
        turing_threshold=config.turing_threshold,
        quantum_jitter=config.quantum_jitter,
        jitter_var=config.jitter_var,
        spike_probability=config.spike_probability,
        random_seed=config.seed,
        check_stability=True,
        neuromodulation=config.neuromodulation,
    )

    # Create and run the engine
    engine = ReactionDiffusionEngine(rd_config)

    # Run simulation with history for tracking
    field, metrics = engine.simulate(
        steps=config.steps,
        turing_enabled=config.turing_enabled,
        return_history=False,
    )

    elapsed_time = time.perf_counter() - start_time

    # Build typed simulation metrics
    sim_metrics = SimulationMetrics(
        elapsed_time_s=elapsed_time,
        steps_computed=metrics.steps_computed,
        field_min_v=metrics.field_min_v,
        field_max_v=metrics.field_max_v,
        field_mean_v=metrics.field_mean_v,
        field_std_v=metrics.field_std_v,
        activator_mean=metrics.activator_mean,
        inhibitor_mean=metrics.inhibitor_mean,
        turing_activations=metrics.turing_activations,
        clamping_events=metrics.clamping_events,
        plasticity_index_mean=metrics.plasticity_index_mean,
        effective_inhibition_mean=metrics.effective_inhibition_mean,
        effective_gain_mean=metrics.effective_gain_mean,
        observation_noise_gain_mean=metrics.observation_noise_gain_mean,
        occupancy_resting_mean=metrics.occupancy_resting_mean,
        occupancy_active_mean=metrics.occupancy_active_mean,
        occupancy_desensitized_mean=metrics.occupancy_desensitized_mean,
        occupancy_mass_error_max=metrics.occupancy_mass_error_max,
        excitability_offset_mean_v=metrics.excitability_offset_mean_v,
        alpha_guard_triggered=metrics.alpha_guard_triggered,
        alpha_guard_triggers=metrics.alpha_guard_triggers,
        substeps_used=metrics.substeps_used,
        effective_dt=metrics.effective_dt,
        soft_boundary_pressure=metrics.soft_boundary_pressure,
        hard_clamp_events=metrics.hard_clamp_events,
    )

    # Build metadata: typed metrics + config snapshot for backward compat
    metadata: dict[str, Any] = sim_metrics.to_dict()
    metadata["config"] = config.to_dict()

    final_field: NDArray[np.float64] = field.astype(np.float64)

    return SimulationResult(
        field=final_field,
        history=None,
        growth_events=metrics.growth_events,
        turing_activations=metrics.turing_activations,
        clamping_events=metrics.clamping_events,
        metadata=metadata,
    )


def run_mycelium_simulation_with_history(
    config: SimulationConfig,
) -> SimulationResult:
    """
    Run a mycelium field simulation with full history tracking.

    Similar to run_mycelium_simulation but stores the field state at each
    timestep, enabling analysis of temporal dynamics and feature extraction.

    Args:
        config: SimulationConfig with simulation parameters. See
            run_mycelium_simulation for parameter details.

    Returns:
        SimulationResult containing:
            - field: Final 2D potential field in Volts (N × N).
            - history: Time series array of shape (steps, grid_size, grid_size).
            - growth_events: Total number of growth events during simulation.
            - metadata: Dict with timing, parameters, and simulation metrics.

    Raises:
        TypeError: If config is not a SimulationConfig instance.
        ValueError: If config parameters are invalid.
        StabilityError: If numerical instability is detected during simulation.

    Examples:
        >>> from mycelium_fractal_net import SimulationConfig
        >>> from mycelium_fractal_net import run_mycelium_simulation_with_history
        >>> config = SimulationConfig(grid_size=32, steps=10, seed=42)
        >>> result = run_mycelium_simulation_with_history(config)
        >>> result.history.shape
        (10, 32, 32)
        >>> result.has_history
        True

    Notes:
        - Uses more memory than run_mycelium_simulation (O(steps * N²)).
        - For large grids or many steps, consider using the base function.
        - History is required for temporal feature extraction (dV_mean, etc.).
        - Does not modify the input config object.
    """
    if not isinstance(config, SimulationConfig):
        raise TypeError(f"config must be SimulationConfig, got {type(config).__name__}")

    start_time = time.perf_counter()

    # Create RD engine configuration
    rd_config = ReactionDiffusionConfig(
        grid_size=config.grid_size,
        alpha=config.alpha,
        turing_threshold=config.turing_threshold,
        quantum_jitter=config.quantum_jitter,
        jitter_var=config.jitter_var,
        spike_probability=config.spike_probability,
        random_seed=config.seed,
        check_stability=True,
        neuromodulation=config.neuromodulation,
    )

    engine = ReactionDiffusionEngine(rd_config)

    # Run simulation WITH history
    history_arr, metrics = engine.simulate(
        steps=config.steps,
        turing_enabled=config.turing_enabled,
        return_history=True,
    )

    elapsed_time = time.perf_counter() - start_time

    # Get final field from history
    final_field: NDArray[np.float64] = history_arr[-1].astype(np.float64)
    history: NDArray[np.float64] = history_arr.astype(np.float64)

    sim_metrics = SimulationMetrics(
        elapsed_time_s=elapsed_time,
        steps_computed=metrics.steps_computed,
        field_min_v=metrics.field_min_v,
        field_max_v=metrics.field_max_v,
        field_mean_v=metrics.field_mean_v,
        field_std_v=metrics.field_std_v,
        activator_mean=metrics.activator_mean,
        inhibitor_mean=metrics.inhibitor_mean,
        turing_activations=metrics.turing_activations,
        clamping_events=metrics.clamping_events,
        plasticity_index_mean=metrics.plasticity_index_mean,
        effective_inhibition_mean=metrics.effective_inhibition_mean,
        effective_gain_mean=metrics.effective_gain_mean,
        observation_noise_gain_mean=metrics.observation_noise_gain_mean,
        occupancy_resting_mean=metrics.occupancy_resting_mean,
        occupancy_active_mean=metrics.occupancy_active_mean,
        occupancy_desensitized_mean=metrics.occupancy_desensitized_mean,
        occupancy_mass_error_max=metrics.occupancy_mass_error_max,
        excitability_offset_mean_v=metrics.excitability_offset_mean_v,
        alpha_guard_triggered=metrics.alpha_guard_triggered,
        alpha_guard_triggers=metrics.alpha_guard_triggers,
        substeps_used=metrics.substeps_used,
        effective_dt=metrics.effective_dt,
        soft_boundary_pressure=metrics.soft_boundary_pressure,
        hard_clamp_events=metrics.hard_clamp_events,
    )

    metadata: dict[str, Any] = sim_metrics.to_dict()
    metadata["config"] = config.to_dict()

    return SimulationResult(
        field=final_field,
        history=history,
        growth_events=metrics.growth_events,
        turing_activations=metrics.turing_activations,
        clamping_events=metrics.clamping_events,
        metadata=metadata,
    )
