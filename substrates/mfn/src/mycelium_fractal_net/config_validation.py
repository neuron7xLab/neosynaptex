"""Configuration validation and factory functions."""

from __future__ import annotations

from pathlib import Path

from mycelium_fractal_net.config import (
    ALPHA_MAX,
    ALPHA_MIN,
    BOX_SIZE_MIN,
    CONNECTIVITY_VALUES,
    GRID_SIZE_MAX,
    GRID_SIZE_MIN,
    JITTER_VAR_MAX,
    JITTER_VAR_MIN,
    NUM_SAMPLES_MAX,
    NUM_SAMPLES_MIN,
    NUM_SCALES_MAX,
    NUM_SCALES_MIN,
    PROBABILITY_MAX,
    PROBABILITY_MIN,
    STEPS_MAX,
    STEPS_MIN,
    THRESHOLD_MV_MAX,
    THRESHOLD_MV_MIN,
    TURING_THRESHOLD_MAX,
    TURING_THRESHOLD_MIN,
    DatasetConfig,
    FeatureConfig,
)
from mycelium_fractal_net.core.types import SimulationConfig


def validate_simulation_config(config: SimulationConfig) -> None:
    """
    Validate SimulationConfig parameters.

    Checks all invariants and parameter bounds defined in MFN_MATH_MODEL.md.
    This function performs stricter validation than the built-in __post_init__.

    Args:
        config: SimulationConfig instance to validate.

    Raises:
        TypeError: If config is not a SimulationConfig instance.
        ValueError: If any parameter violates its constraints:
            - grid_size not in [4, 512]
            - steps not in [1, 10000]
            - alpha not in (0, 0.25]
            - spike_probability not in [0, 1]
            - turing_threshold not in [0, 1]
            - jitter_var not in [0, 0.01]
            - seed is not None and not an integer
    """
    if not isinstance(config, SimulationConfig):
        raise TypeError(f"Expected SimulationConfig, got {type(config).__name__}")

    # grid_size
    if not isinstance(config.grid_size, int):
        raise ValueError(f"grid_size must be int, got {type(config.grid_size).__name__}")
    if not (GRID_SIZE_MIN <= config.grid_size <= GRID_SIZE_MAX):
        raise ValueError(
            f"grid_size must be in [{GRID_SIZE_MIN}, {GRID_SIZE_MAX}], got {config.grid_size}"
        )

    # steps
    if not isinstance(config.steps, int):
        raise ValueError(f"steps must be int, got {type(config.steps).__name__}")
    if not (STEPS_MIN <= config.steps <= STEPS_MAX):
        raise ValueError(f"steps must be in [{STEPS_MIN}, {STEPS_MAX}], got {config.steps}")

    # alpha (CFL stability)
    if not isinstance(config.alpha, (int, float)):
        raise ValueError(f"alpha must be numeric, got {type(config.alpha).__name__}")
    if not (ALPHA_MIN < config.alpha <= ALPHA_MAX):
        raise ValueError(
            f"alpha must be in ({ALPHA_MIN}, {ALPHA_MAX}] for CFL stability, got {config.alpha}"
        )

    # spike_probability
    if not isinstance(config.spike_probability, (int, float)):
        raise ValueError(
            f"spike_probability must be numeric, got {type(config.spike_probability).__name__}"
        )
    if not (PROBABILITY_MIN <= config.spike_probability <= PROBABILITY_MAX):
        raise ValueError(
            f"spike_probability must be in [{PROBABILITY_MIN}, {PROBABILITY_MAX}], "
            f"got {config.spike_probability}"
        )

    # turing_enabled
    if not isinstance(config.turing_enabled, bool):
        raise ValueError(f"turing_enabled must be bool, got {type(config.turing_enabled).__name__}")

    # turing_threshold
    if not isinstance(config.turing_threshold, (int, float)):
        raise ValueError(
            f"turing_threshold must be numeric, got {type(config.turing_threshold).__name__}"
        )
    if not (TURING_THRESHOLD_MIN <= config.turing_threshold <= TURING_THRESHOLD_MAX):
        raise ValueError(
            f"turing_threshold must be in [{TURING_THRESHOLD_MIN}, {TURING_THRESHOLD_MAX}], "
            f"got {config.turing_threshold}"
        )

    # quantum_jitter
    if not isinstance(config.quantum_jitter, bool):
        raise ValueError(f"quantum_jitter must be bool, got {type(config.quantum_jitter).__name__}")

    # jitter_var
    if not isinstance(config.jitter_var, (int, float)):
        raise ValueError(f"jitter_var must be numeric, got {type(config.jitter_var).__name__}")
    if not (JITTER_VAR_MIN <= config.jitter_var <= JITTER_VAR_MAX):
        raise ValueError(
            f"jitter_var must be in [{JITTER_VAR_MIN}, {JITTER_VAR_MAX}], got {config.jitter_var}"
        )

    # seed
    if config.seed is not None and not isinstance(config.seed, int):
        raise ValueError(f"seed must be int or None, got {type(config.seed).__name__}")


def validate_feature_config(config: FeatureConfig) -> None:
    """
    Validate FeatureConfig parameters.

    Checks all invariants for feature extraction as defined in MFN_FEATURE_SCHEMA.md.

    Args:
        config: FeatureConfig instance to validate.

    Raises:
        TypeError: If config is not a FeatureConfig instance.
        ValueError: If any parameter violates its constraints:
            - min_box_size < 1
            - max_box_size < min_box_size (when not None)
            - num_scales not in [2, 20]
            - threshold values not in [-100, 50] mV
            - threshold_low_mv > threshold_med_mv > threshold_high_mv (order violation)
            - stability_window < 1
            - connectivity not in {4, 8}
    """
    if not isinstance(config, FeatureConfig):
        raise TypeError(f"Expected FeatureConfig, got {type(config).__name__}")

    # min_box_size
    if not isinstance(config.min_box_size, int):
        raise ValueError(f"min_box_size must be int, got {type(config.min_box_size).__name__}")
    if config.min_box_size < BOX_SIZE_MIN:
        raise ValueError(f"min_box_size must be >= {BOX_SIZE_MIN}, got {config.min_box_size}")

    # max_box_size
    if config.max_box_size is not None:
        if not isinstance(config.max_box_size, int):
            raise ValueError(
                f"max_box_size must be int or None, got {type(config.max_box_size).__name__}"
            )
        if config.max_box_size < config.min_box_size:
            raise ValueError(
                f"max_box_size ({config.max_box_size}) must be >= "
                f"min_box_size ({config.min_box_size})"
            )

    # num_scales
    if not isinstance(config.num_scales, int):
        raise ValueError(f"num_scales must be int, got {type(config.num_scales).__name__}")
    if not (NUM_SCALES_MIN <= config.num_scales <= NUM_SCALES_MAX):
        raise ValueError(
            f"num_scales must be in [{NUM_SCALES_MIN}, {NUM_SCALES_MAX}], got {config.num_scales}"
        )

    # threshold values
    for name in ("threshold_low_mv", "threshold_med_mv", "threshold_high_mv"):
        value = getattr(config, name)
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric, got {type(value).__name__}")
        if not (THRESHOLD_MV_MIN <= value <= THRESHOLD_MV_MAX):
            raise ValueError(
                f"{name} must be in [{THRESHOLD_MV_MIN}, {THRESHOLD_MV_MAX}], got {value}"
            )

    # Threshold order: low < med < high
    if config.threshold_low_mv >= config.threshold_med_mv:
        raise ValueError(
            f"threshold_low_mv ({config.threshold_low_mv}) must be < "
            f"threshold_med_mv ({config.threshold_med_mv})"
        )
    if config.threshold_med_mv >= config.threshold_high_mv:
        raise ValueError(
            f"threshold_med_mv ({config.threshold_med_mv}) must be < "
            f"threshold_high_mv ({config.threshold_high_mv})"
        )

    # stability_threshold_mv
    if not isinstance(config.stability_threshold_mv, (int, float)):
        raise ValueError(
            f"stability_threshold_mv must be numeric, got "
            f"{type(config.stability_threshold_mv).__name__}"
        )
    if config.stability_threshold_mv < 0:
        raise ValueError(
            f"stability_threshold_mv must be >= 0, got {config.stability_threshold_mv}"
        )

    # stability_window
    if not isinstance(config.stability_window, int):
        raise ValueError(
            f"stability_window must be int, got {type(config.stability_window).__name__}"
        )
    if config.stability_window < 1:
        raise ValueError(f"stability_window must be >= 1, got {config.stability_window}")

    # connectivity
    if not isinstance(config.connectivity, int):
        raise ValueError(f"connectivity must be int, got {type(config.connectivity).__name__}")
    if config.connectivity not in CONNECTIVITY_VALUES:
        raise ValueError(
            f"connectivity must be one of {CONNECTIVITY_VALUES}, got {config.connectivity}"
        )


def validate_dataset_config(config: DatasetConfig) -> None:
    """
    Validate DatasetConfig parameters.

    Checks all invariants for dataset generation as defined in MFN_DATASET_SPEC.md.

    Args:
        config: DatasetConfig instance to validate.

    Raises:
        TypeError: If config is not a DatasetConfig instance.
        ValueError: If any parameter violates its constraints:
            - num_samples not in [1, 100000]
            - grid_sizes empty or any value not in [4, 512]
            - steps_range invalid (min > max, values outside [1, 10000])
            - alpha_range invalid (min >= max, values outside (0, 0.25))
            - turing_values empty
            - spike_prob_range invalid
            - turing_threshold_range invalid
    """
    if not isinstance(config, DatasetConfig):
        raise TypeError(f"Expected DatasetConfig, got {type(config).__name__}")

    # num_samples
    if not isinstance(config.num_samples, int):
        raise ValueError(f"num_samples must be int, got {type(config.num_samples).__name__}")
    if not (NUM_SAMPLES_MIN <= config.num_samples <= NUM_SAMPLES_MAX):
        raise ValueError(
            f"num_samples must be in [{NUM_SAMPLES_MIN}, {NUM_SAMPLES_MAX}], "
            f"got {config.num_samples}"
        )

    # grid_sizes
    if not isinstance(config.grid_sizes, list):
        raise ValueError(f"grid_sizes must be list, got {type(config.grid_sizes).__name__}")
    if len(config.grid_sizes) == 0:
        raise ValueError("grid_sizes must not be empty")
    for i, gs in enumerate(config.grid_sizes):
        if not isinstance(gs, int):
            raise ValueError(f"grid_sizes[{i}] must be int, got {type(gs).__name__}")
        if not (GRID_SIZE_MIN <= gs <= GRID_SIZE_MAX):
            raise ValueError(
                f"grid_sizes[{i}] must be in [{GRID_SIZE_MIN}, {GRID_SIZE_MAX}], got {gs}"
            )

    # steps_range
    if not isinstance(config.steps_range, tuple) or len(config.steps_range) != 2:
        raise ValueError("steps_range must be tuple of (min, max)")
    smin, smax = config.steps_range
    if not (isinstance(smin, int) and isinstance(smax, int)):
        raise ValueError("steps_range values must be int")
    if smin > smax:
        raise ValueError(f"steps_range min ({smin}) must be <= max ({smax})")
    if not (STEPS_MIN <= smin <= STEPS_MAX and STEPS_MIN <= smax <= STEPS_MAX):
        raise ValueError(f"steps_range must be in [{STEPS_MIN}, {STEPS_MAX}]")

    # alpha_range
    if not isinstance(config.alpha_range, tuple) or len(config.alpha_range) != 2:
        raise ValueError("alpha_range must be tuple of (min, max)")
    amin, amax = config.alpha_range
    if not (isinstance(amin, (int, float)) and isinstance(amax, (int, float))):
        raise ValueError("alpha_range values must be numeric")
    if amin >= amax:
        raise ValueError(f"alpha_range min ({amin}) must be < max ({amax})")
    if not (amin > ALPHA_MIN and amax <= ALPHA_MAX):
        raise ValueError(f"alpha_range must be in ({ALPHA_MIN}, {ALPHA_MAX}] for CFL stability")

    # turing_values
    if not isinstance(config.turing_values, list):
        raise ValueError(f"turing_values must be list, got {type(config.turing_values).__name__}")
    if len(config.turing_values) == 0:
        raise ValueError("turing_values must not be empty")
    for i, tv in enumerate(config.turing_values):
        if not isinstance(tv, bool):
            raise ValueError(f"turing_values[{i}] must be bool, got {type(tv).__name__}")

    # spike_prob_range
    if not isinstance(config.spike_prob_range, tuple) or len(config.spike_prob_range) != 2:
        raise ValueError("spike_prob_range must be tuple of (min, max)")
    spmin, spmax = config.spike_prob_range
    if not (isinstance(spmin, (int, float)) and isinstance(spmax, (int, float))):
        raise ValueError("spike_prob_range values must be numeric")
    if spmin > spmax:
        raise ValueError(f"spike_prob_range min ({spmin}) must be <= max ({spmax})")
    if not (
        PROBABILITY_MIN <= spmin <= PROBABILITY_MAX and PROBABILITY_MIN <= spmax <= PROBABILITY_MAX
    ):
        raise ValueError(f"spike_prob_range must be in [{PROBABILITY_MIN}, {PROBABILITY_MAX}]")

    # turing_threshold_range
    if (
        not isinstance(config.turing_threshold_range, tuple)
        or len(config.turing_threshold_range) != 2
    ):
        raise ValueError("turing_threshold_range must be tuple of (min, max)")
    ttmin, ttmax = config.turing_threshold_range
    if not (isinstance(ttmin, (int, float)) and isinstance(ttmax, (int, float))):
        raise ValueError("turing_threshold_range values must be numeric")
    if ttmin > ttmax:
        raise ValueError(f"turing_threshold_range min ({ttmin}) must be <= max ({ttmax})")
    if not (
        TURING_THRESHOLD_MIN <= ttmin <= TURING_THRESHOLD_MAX
        and TURING_THRESHOLD_MIN <= ttmax <= TURING_THRESHOLD_MAX
    ):
        raise ValueError(
            f"turing_threshold_range must be in [{TURING_THRESHOLD_MIN}, {TURING_THRESHOLD_MAX}]"
        )

    # base_seed
    if not isinstance(config.base_seed, int):
        raise ValueError(f"base_seed must be int, got {type(config.base_seed).__name__}")

    # output_path
    if not isinstance(config.output_path, Path):
        raise ValueError(f"output_path must be Path, got {type(config.output_path).__name__}")


# ============================================================================
# Factory Functions
# ============================================================================


def make_simulation_config_demo() -> SimulationConfig:
    """
    Create a demo SimulationConfig for quick testing.

    Returns a configuration with small grid and few steps,
    suitable for fast iteration and demos.

    Returns:
        SimulationConfig with demo parameters:
            - grid_size: 32
            - steps: 32
            - seed: 42 (for reproducibility)

    Raises:
        ValueError: If validation fails (should not occur with default values).
    """
    config = SimulationConfig(
        grid_size=32,
        steps=32,
        alpha=0.18,
        spike_probability=0.25,
        turing_enabled=True,
        turing_threshold=0.75,
        quantum_jitter=False,
        jitter_var=0.0005,
        seed=42,
    )
    validate_simulation_config(config)
    return config


def make_simulation_config_default() -> SimulationConfig:
    """
    Create a default SimulationConfig for standard simulations.

    Returns a configuration with standard parameters suitable for
    typical analysis and production use.

    Returns:
        SimulationConfig with default parameters:
            - grid_size: 64
            - steps: 100
            - seed: 42 (for reproducibility)

    Raises:
        ValueError: If validation fails (should not occur with default values).
    """
    config = SimulationConfig(
        grid_size=64,
        steps=100,
        alpha=0.18,
        spike_probability=0.25,
        turing_enabled=True,
        turing_threshold=0.75,
        quantum_jitter=False,
        jitter_var=0.0005,
        seed=42,
    )
    validate_simulation_config(config)
    return config


def make_feature_config_demo() -> FeatureConfig:
    """
    Create a demo FeatureConfig for quick testing.

    Returns:
        FeatureConfig with demo parameters optimized for fast computation.

    Raises:
        ValueError: If validation fails (should not occur with default values).
    """
    return FeatureConfig(
        min_box_size=2,
        max_box_size=None,
        num_scales=3,
        threshold_low_mv=-60.0,
        threshold_med_mv=-50.0,
        threshold_high_mv=-40.0,
        stability_threshold_mv=0.001,
        stability_window=5,
        connectivity=4,
    )


def make_feature_config_default() -> FeatureConfig:
    """
    Create a default FeatureConfig for standard feature extraction.

    Returns:
        FeatureConfig with default parameters per MFN_FEATURE_SCHEMA.md.

    Raises:
        ValueError: If validation fails (should not occur with default values).
    """
    return FeatureConfig(
        min_box_size=2,
        max_box_size=None,
        num_scales=5,
        threshold_low_mv=-60.0,
        threshold_med_mv=-50.0,
        threshold_high_mv=-40.0,
        stability_threshold_mv=0.001,
        stability_window=10,
        connectivity=4,
    )


def make_dataset_config_demo() -> DatasetConfig:
    """
    Create a demo DatasetConfig for quick testing.

    Returns a configuration for generating a small dataset
    suitable for fast iteration and testing.

    Returns:
        DatasetConfig with demo parameters:
            - num_samples: 10
            - grid_sizes: [32]
            - Small parameter ranges

    Raises:
        ValueError: If validation fails (should not occur with default values).
    """
    return DatasetConfig(
        num_samples=10,
        grid_sizes=[32],
        steps_range=(30, 50),
        alpha_range=(0.15, 0.18),
        turing_values=[True],
        spike_prob_range=(0.20, 0.30),
        turing_threshold_range=(0.70, 0.80),
        base_seed=42,
        output_path=Path("data/mfn_dataset_demo.parquet"),
    )


def make_dataset_config_default() -> DatasetConfig:
    """
    Create a default DatasetConfig for standard dataset generation.

    Returns a configuration for generating a standard dataset
    as specified in MFN_DATASET_SPEC.md.

    Returns:
        DatasetConfig with default parameters:
            - num_samples: 200
            - grid_sizes: [32, 64]
            - Standard parameter ranges

    Raises:
        ValueError: If validation fails (should not occur with default values).
    """
    return DatasetConfig(
        num_samples=200,
        grid_sizes=[32, 64],
        steps_range=(50, 200),
        alpha_range=(0.10, 0.20),
        turing_values=[True, False],
        spike_prob_range=(0.15, 0.35),
        turing_threshold_range=(0.65, 0.85),
        base_seed=42,
        output_path=Path("data/mfn_dataset.parquet"),
    )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ALPHA_MAX",
    "ALPHA_MIN",
    "GRID_SIZE_MAX",
    # Constants
    "GRID_SIZE_MIN",
    "STEPS_MAX",
    "STEPS_MIN",
    "DatasetConfig",
    "FeatureConfig",
    # Config classes
    "SimulationConfig",
    "make_dataset_config_default",
    "make_dataset_config_demo",
    "make_feature_config_default",
    "make_feature_config_demo",
    "make_simulation_config_default",
    # Factory functions
    "make_simulation_config_demo",
    "validate_dataset_config",
    "validate_feature_config",
    # Validation functions
    "validate_simulation_config",
]
