"""
Centralized Configuration Module for MyceliumFractalNet.

Provides unified configuration dataclasses with validation and factory functions
for simulation, feature extraction, and dataset generation.

This module serves as the single source of truth for all MFN configurations.

Usage:
    >>> from mycelium_fractal_net.config import (
    ...     SimulationConfig, FeatureConfig, DatasetConfig,
    ...     make_simulation_config_demo, make_dataset_config_default,
    ... )
    >>> config = make_simulation_config_demo()
    >>> print(config.grid_size, config.steps)

Reference: docs/MFN_MATH_MODEL.md, docs/MFN_FEATURE_SCHEMA.md, docs/MFN_DATASET_SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Re-export SimulationConfig from core.types (single source of truth)

# ============================================================================
# Constants - Parameter Bounds
# ============================================================================

# Grid size bounds
GRID_SIZE_MIN: int = 4
GRID_SIZE_MAX: int = 512

# Simulation steps bounds
STEPS_MIN: int = 1
STEPS_MAX: int = 10000

# Diffusion coefficient bounds (CFL stability requires alpha <= 0.25)
ALPHA_MIN: float = 0.001
ALPHA_MAX: float = 0.25

# Probability bounds
PROBABILITY_MIN: float = 0.0
PROBABILITY_MAX: float = 1.0

# Turing threshold bounds
TURING_THRESHOLD_MIN: float = 0.0
TURING_THRESHOLD_MAX: float = 1.0

# Jitter variance bounds
JITTER_VAR_MIN: float = 0.0
JITTER_VAR_MAX: float = 0.01

# Feature extraction bounds
NUM_SCALES_MIN: int = 2
NUM_SCALES_MAX: int = 20
BOX_SIZE_MIN: int = 1
CONNECTIVITY_VALUES: tuple[int, ...] = (4, 8)

# Threshold bounds for structural features (mV)
THRESHOLD_MV_MIN: float = -100.0
THRESHOLD_MV_MAX: float = 50.0

# Dataset generation bounds
NUM_SAMPLES_MIN: int = 1
NUM_SAMPLES_MAX: int = 100000
SEEDS_PER_CONFIG_MIN: int = 1
SEEDS_PER_CONFIG_MAX: int = 100


# ============================================================================
# FeatureConfig
# ============================================================================


@dataclass
class FeatureConfig:
    """
    Configuration for feature extraction.

    Defines parameters for box-counting dimension, structural features,
    and temporal analysis as specified in MFN_FEATURE_SCHEMA.md.

    Attributes:
        min_box_size: Minimum box size for box-counting. Range: [1, ∞). Default: 2.
        max_box_size: Maximum box size. None = grid_size // 2.
        num_scales: Number of scales for dimension estimation. Range: [2, 20]. Default: 5.
        threshold_low_mv: Low threshold for structural features (mV). Default: -60.0.
        threshold_med_mv: Medium threshold (mV). Default: -50.0.
        threshold_high_mv: High threshold (mV). Default: -40.0.
        stability_threshold_mv: Threshold for quasi-stationary detection (mV/step). Default: 0.001.
        stability_window: Consecutive steps required for stability. Range: [1, ∞). Default: 10.
        connectivity: Connectivity for cluster detection. Values: {4, 8}. Default: 4.
    """

    min_box_size: int = 2
    max_box_size: int | None = None
    num_scales: int = 5
    threshold_low_mv: float = -60.0
    threshold_med_mv: float = -50.0
    threshold_high_mv: float = -40.0
    stability_threshold_mv: float = 0.001
    stability_window: int = 10
    connectivity: int = 4

    def __post_init__(self) -> None:
        """Validate all parameters on construction."""
        validate_feature_config(self)

    def to_dict(self) -> dict[str, object]:
        """
        Serialize configuration to a dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "min_box_size": self.min_box_size,
            "max_box_size": self.max_box_size,
            "num_scales": self.num_scales,
            "threshold_low_mv": self.threshold_low_mv,
            "threshold_med_mv": self.threshold_med_mv,
            "threshold_high_mv": self.threshold_high_mv,
            "stability_threshold_mv": self.stability_threshold_mv,
            "stability_window": self.stability_window,
            "connectivity": self.connectivity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeatureConfig:
        """
        Create configuration from a dictionary.

        Args:
            data: Dictionary with configuration values.

        Returns:
            New FeatureConfig instance.
        """
        min_box_value = data.get("min_box_size")
        max_box_value = data.get("max_box_size")
        num_scales_value = data.get("num_scales")
        threshold_low_value = data.get("threshold_low_mv")
        threshold_med_value = data.get("threshold_med_mv")
        threshold_high_value = data.get("threshold_high_mv")
        stability_threshold_value = data.get("stability_threshold_mv")
        stability_window_value = data.get("stability_window")
        connectivity_value = data.get("connectivity")
        return cls(
            min_box_size=int(min_box_value) if min_box_value is not None else 2,
            max_box_size=int(max_box_value) if max_box_value is not None else None,
            num_scales=int(num_scales_value) if num_scales_value is not None else 5,
            threshold_low_mv=(
                float(threshold_low_value) if threshold_low_value is not None else -60.0
            ),
            threshold_med_mv=(
                float(threshold_med_value) if threshold_med_value is not None else -50.0
            ),
            threshold_high_mv=(
                float(threshold_high_value) if threshold_high_value is not None else -40.0
            ),
            stability_threshold_mv=(
                float(stability_threshold_value) if stability_threshold_value is not None else 0.001
            ),
            stability_window=(
                int(stability_window_value) if stability_window_value is not None else 10
            ),
            connectivity=(int(connectivity_value) if connectivity_value is not None else 4),
        )


@dataclass
class DatasetConfig:
    """
    Configuration for dataset generation.

    Defines parameter ranges for simulation sweep and output settings
    as specified in MFN_DATASET_SPEC.md.

    Attributes:
        num_samples: Number of simulations to generate. Range: [1, 100000]. Default: 200.
        grid_sizes: Grid sizes to sample from. All must be in [4, 512]. Default: [32, 64].
        steps_range: (min, max) steps to sample. Range: [1, 10000]. Default: (50, 200).
        alpha_range: (min, max) diffusion coefficient. Range: (0, 0.25). Default: (0.10, 0.20).
        turing_values: Turing enabled values to sample. Default: [True, False].
        spike_prob_range: (min, max) spike probability. Range: [0, 1]. Default: (0.15, 0.35).
        turing_threshold_range: (min, max) Turing threshold. Range: [0, 1]. Default: (0.65, 0.85).
        base_seed: Base seed for reproducibility. Default: 42.
        output_path: Output path for dataset file. Default: data/mfn_dataset.parquet.
    """

    num_samples: int = 200
    grid_sizes: list[int] = field(default_factory=lambda: [32, 64])
    steps_range: tuple[int, int] = (50, 200)
    alpha_range: tuple[float, float] = (0.10, 0.20)
    turing_values: list[bool] = field(default_factory=lambda: [True, False])
    spike_prob_range: tuple[float, float] = (0.15, 0.35)
    turing_threshold_range: tuple[float, float] = (0.65, 0.85)
    base_seed: int = 42
    output_path: Path = field(default_factory=lambda: Path("data/mfn_dataset.parquet"))

    def __post_init__(self) -> None:
        """Validate all parameters on construction."""
        validate_dataset_config(self)

    def to_dict(self) -> dict[str, object]:
        """
        Serialize configuration to a dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "num_samples": self.num_samples,
            "grid_sizes": self.grid_sizes,
            "steps_range": list(self.steps_range),
            "alpha_range": list(self.alpha_range),
            "turing_values": self.turing_values,
            "spike_prob_range": list(self.spike_prob_range),
            "turing_threshold_range": list(self.turing_threshold_range),
            "base_seed": self.base_seed,
            "output_path": str(self.output_path),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetConfig:
        """
        Create configuration from a dictionary.

        Args:
            data: Dictionary with configuration values.

        Returns:
            New DatasetConfig instance.
        """
        steps_range_raw = data["steps_range"] if data.get("steps_range") is not None else (50, 200)
        alpha_range_raw = (
            data["alpha_range"] if data.get("alpha_range") is not None else (0.10, 0.20)
        )
        spike_prob_range_raw = (
            data["spike_prob_range"] if data.get("spike_prob_range") is not None else (0.15, 0.35)
        )
        turing_threshold_range_raw = (
            data["turing_threshold_range"]
            if data.get("turing_threshold_range") is not None
            else (0.65, 0.85)
        )

        # Convert to list for safe indexing
        steps_range_list = list(steps_range_raw)
        if len(steps_range_list) != 2:
            raise ValueError("steps_range must contain exactly two values (min, max)")

        alpha_range_list = list(alpha_range_raw)
        if len(alpha_range_list) != 2:
            raise ValueError("alpha_range must contain exactly two values (min, max)")

        spike_prob_range_list = list(spike_prob_range_raw)
        if len(spike_prob_range_list) != 2:
            raise ValueError("spike_prob_range must contain exactly two values (min, max)")

        turing_threshold_range_list = list(turing_threshold_range_raw)
        if len(turing_threshold_range_list) != 2:
            raise ValueError("turing_threshold_range must contain exactly two values (min, max)")

        grid_sizes_raw = data["grid_sizes"] if data.get("grid_sizes") is not None else [32, 64]
        turing_values_raw = (
            data["turing_values"] if data.get("turing_values") is not None else [True, False]
        )

        num_samples_value = data.get("num_samples")
        base_seed_value = data.get("base_seed")

        return cls(
            num_samples=(int(num_samples_value) if num_samples_value is not None else 200),
            grid_sizes=list(grid_sizes_raw),
            steps_range=(int(steps_range_list[0]), int(steps_range_list[1])),
            alpha_range=(float(alpha_range_list[0]), float(alpha_range_list[1])),
            turing_values=list(turing_values_raw),
            spike_prob_range=(
                float(spike_prob_range_list[0]),
                float(spike_prob_range_list[1]),
            ),
            turing_threshold_range=(
                float(turing_threshold_range_list[0]),
                float(turing_threshold_range_list[1]),
            ),
            base_seed=int(base_seed_value) if base_seed_value is not None else 42,
            output_path=Path(
                str(
                    data["output_path"]
                    if data.get("output_path") is not None
                    else "data/mfn_dataset.parquet"
                )
            ),
        )


# ============================================================================
# Validation Functions
# ============================================================================


# Validation and factory functions extracted to config_validation.py
from mycelium_fractal_net.config_validation import (  # noqa: F401
    make_dataset_config_default,
    make_dataset_config_demo,
    make_feature_config_default,
    make_feature_config_demo,
    make_simulation_config_default,
    make_simulation_config_demo,
    validate_dataset_config,
    validate_feature_config,
    validate_simulation_config,
)

# Re-export SimulationConfig for backward compatibility
from mycelium_fractal_net.core.types import (
    SimulationConfig as SimulationConfig,  # noqa: PLC0414
)
