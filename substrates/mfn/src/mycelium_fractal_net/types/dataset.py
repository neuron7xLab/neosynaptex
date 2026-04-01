"""
Dataset types for MyceliumFractalNet data pipelines.

Defines canonical types for dataset rows, metadata, and statistics.
These types correspond to the schema defined in MFN_DATA_PIPELINES.md.

Reference:
    - docs/MFN_DATA_PIPELINES.md Section 5 — Dataset Schema
    - docs/MFN_FEATURE_SCHEMA.md — Feature definitions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

# Import canonical feature names
from .features import FEATURE_NAMES

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Simulation parameter column names (per MFN_DATA_PIPELINES.md Section 5.1)
SIMULATION_PARAM_COLUMNS: list[str] = [
    "sim_id",
    "scenario_name",
    "grid_size",
    "steps",
    "alpha",
    "turing_enabled",
    "random_seed",
]

# Simulation metadata column names (per MFN_DATA_PIPELINES.md Section 5.3)
SIMULATION_META_COLUMNS: list[str] = [
    "growth_events",
    "turing_activations",
    "clamping_events",
]

# All expected columns in canonical order
ALL_DATASET_COLUMNS: list[str] = SIMULATION_PARAM_COLUMNS + FEATURE_NAMES + SIMULATION_META_COLUMNS


@dataclass
class DatasetRow:
    """
    Represents a single row in an MFN dataset.

    Each row contains simulation parameters, all 18 features, and metadata.
    This type ensures type safety and validation for dataset operations.

    Attributes:
        sim_id: Unique simulation identifier
        scenario_name: Name of the scenario that generated this row
        grid_size: Grid dimension N (N×N)
        steps: Number of simulation steps
        alpha: Diffusion coefficient
        turing_enabled: Whether Turing morphogenesis was enabled
        random_seed: Random seed for reproducibility
        features: Dictionary of 18 fractal features
        growth_events: Number of growth events during simulation
        turing_activations: Number of Turing activation events
        clamping_events: Number of field clamping events

    Reference:
        docs/MFN_DATA_PIPELINES.md Section 5 — Dataset Schema
    """

    # Simulation parameters
    sim_id: int
    scenario_name: str
    grid_size: int
    steps: int
    alpha: float
    turing_enabled: bool
    random_seed: int

    # Features (dictionary for flexibility)
    features: dict[str, float] = field(default_factory=dict)

    # Simulation metadata
    growth_events: int = 0
    turing_activations: int = 0
    clamping_events: int = 0

    def __post_init__(self) -> None:
        """Validate row data."""
        if self.sim_id < 0:
            raise ValueError(f"sim_id must be >= 0, got {self.sim_id}")
        if self.grid_size < 2:
            raise ValueError(f"grid_size must be >= 2, got {self.grid_size}")
        if self.steps < 1:
            raise ValueError(f"steps must be >= 1, got {self.steps}")
        if not (0.0 < self.alpha <= 0.25):
            raise ValueError(f"alpha must be in (0, 0.25], got {self.alpha}")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to flat dictionary suitable for DataFrame row.

        Returns:
            Dictionary with all columns in canonical order.
        """
        result: dict[str, Any] = {
            "sim_id": self.sim_id,
            "scenario_name": self.scenario_name,
            "grid_size": self.grid_size,
            "steps": self.steps,
            "alpha": self.alpha,
            "turing_enabled": self.turing_enabled,
            "random_seed": self.random_seed,
        }
        # Add features
        result.update(self.features)
        # Add metadata
        result["growth_events"] = self.growth_events
        result["turing_activations"] = self.turing_activations
        result["clamping_events"] = self.clamping_events
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetRow:
        """
        Create DatasetRow from dictionary.

        Args:
            data: Dictionary with simulation params, features, and metadata.

        Returns:
            DatasetRow instance.
        """
        # Extract features
        features = {name: float(data.get(name, 0.0)) for name in FEATURE_NAMES}

        return cls(
            sim_id=int(data.get("sim_id", 0)),
            scenario_name=str(data.get("scenario_name", "")),
            grid_size=int(data.get("grid_size", 64)),
            steps=int(data.get("steps", 100)),
            alpha=float(data.get("alpha", 0.18)),
            turing_enabled=bool(data.get("turing_enabled", True)),
            random_seed=int(data.get("random_seed", 0)),
            features=features,
            growth_events=int(data.get("growth_events", 0)),
            turing_activations=int(data.get("turing_activations", 0)),
            clamping_events=int(data.get("clamping_events", 0)),
        )

    def get_feature(self, name: str) -> float:
        """Get a specific feature value by name."""
        if name not in FEATURE_NAMES:
            raise KeyError(f"Unknown feature: {name}. Valid: {FEATURE_NAMES}")
        return self.features.get(name, 0.0)

    def feature_array(self) -> NDArray[np.float64]:
        """Get features as numpy array in canonical order."""
        return np.array(
            [self.features.get(name, 0.0) for name in FEATURE_NAMES],
            dtype=np.float64,
        )


@dataclass
class DatasetMeta:
    """Metadata about a generated dataset."""

    scenario_name: str
    output_path: Any
    num_rows: int
    num_columns: int
    elapsed_seconds: float
    timestamp: str
    feature_names: list[str]


@dataclass
class DatasetStats:
    """
    Statistical summary of a dataset.

    Provides aggregate statistics over all rows in a dataset for
    validation and quality monitoring.

    Attributes:
        num_rows: Total number of rows
        num_features: Number of feature columns (should be 18)
        scenario_names: Unique scenario names in the dataset
        grid_sizes: Unique grid sizes used
        feature_stats: Per-feature statistics (min, max, mean, std)

    Reference:
        docs/MFN_DATA_PIPELINES.md Section 7 — Data Contract Guarantees
    """

    num_rows: int
    num_features: int
    scenario_names: list[str]
    grid_sizes: list[int]
    feature_stats: dict[str, dict[str, float]] = field(default_factory=dict)

    def has_expected_features(self) -> bool:
        """Check if dataset has all 18 expected features."""
        return self.num_features == len(FEATURE_NAMES)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "num_rows": self.num_rows,
            "num_features": self.num_features,
            "scenario_names": self.scenario_names,
            "grid_sizes": self.grid_sizes,
            "feature_stats": self.feature_stats,
            "has_expected_features": self.has_expected_features(),
        }

    @classmethod
    def from_dataframe(cls, df: Any) -> DatasetStats:
        """
        Compute statistics from a pandas DataFrame.

        Args:
            df: pandas DataFrame with dataset rows.

        Returns:
            DatasetStats instance.
        """
        # Count features present
        feature_cols = [col for col in FEATURE_NAMES if col in df.columns]

        # Compute per-feature statistics
        feature_stats: dict[str, dict[str, float]] = {}
        for col in feature_cols:
            feature_stats[col] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
            }

        return cls(
            num_rows=len(df),
            num_features=len(feature_cols),
            scenario_names=(
                df["scenario_name"].unique().tolist() if "scenario_name" in df.columns else []
            ),
            grid_sizes=(
                sorted(df["grid_size"].unique().tolist()) if "grid_size" in df.columns else []
            ),
            feature_stats=feature_stats,
        )


__all__ = [
    "ALL_DATASET_COLUMNS",
    "SIMULATION_META_COLUMNS",
    "SIMULATION_PARAM_COLUMNS",
    "DatasetMeta",
    "DatasetRow",
    "DatasetStats",
]
