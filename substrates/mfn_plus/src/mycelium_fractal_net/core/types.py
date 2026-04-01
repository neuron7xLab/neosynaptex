"""
Simulation configuration and result types.

Provides dataclass-based types for simulation input/output.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING, Any

import numpy as np

from mycelium_fractal_net.neurochem.config_types import NeuromodulationConfig

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass(frozen=True)
class SimulationMetrics:
    """Strongly-typed simulation output metrics.

    Replaces the untyped metadata dict from engine.py.
    """

    elapsed_time_s: float = 0.0
    steps_computed: int = 0
    field_min_v: float = 0.0
    field_max_v: float = 0.0
    field_mean_v: float = 0.0
    field_std_v: float = 0.0
    activator_mean: float = 0.0
    inhibitor_mean: float = 0.0
    turing_activations: int = 0
    clamping_events: int = 0
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

    @property
    def occupancy_bounds_ok(self) -> bool:
        return self.occupancy_mass_error_max <= 1e-6

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k in self.__dataclass_fields__:
            d[k] = getattr(self, k)
        d["occupancy_bounds_ok"] = self.occupancy_bounds_ok
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationMetrics:
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class SimulationConfig:
    """Configuration parameters for mycelium field simulation.

    ``neuromodulation`` accepts either a ``dict[str, Any]`` or a typed
    ``NeuromodulationSpec``. If a typed spec is provided, it is converted
    to a dict via ``to_dict()`` for engine compatibility.
    """

    grid_size: int = 64
    steps: int = 64
    alpha: float = 0.18
    spike_probability: float = 0.25
    turing_enabled: bool = True
    turing_threshold: float = 0.75
    quantum_jitter: bool = False
    jitter_var: float = 0.0005
    seed: int | None = None
    neuromodulation: NeuromodulationConfig | None = None

    def __post_init__(self) -> None:
        # Normalize: accept typed NeuromodulationSpec, dict, or NeuromodulationConfig
        if isinstance(self.neuromodulation, dict):
            self.neuromodulation = NeuromodulationConfig.from_dict(self.neuromodulation)
        elif self.neuromodulation is not None and not isinstance(
            self.neuromodulation, NeuromodulationConfig
        ):
            # Accept NeuromodulationSpec or any object with to_dict()
            if hasattr(self.neuromodulation, "to_dict"):
                self.neuromodulation = NeuromodulationConfig.from_dict(
                    self.neuromodulation.to_dict()
                )
        if not (4 <= self.grid_size <= 512):
            raise ValueError("grid_size must be in [4, 512]")
        if self.steps < 1:
            raise ValueError("steps must be at least 1")
        if not (0.0 < self.alpha <= 0.25):
            raise ValueError("alpha must be in (0, 0.25] for CFL stability")
        if not (0.0 <= self.spike_probability <= 1.0):
            raise ValueError("spike_probability must be in [0, 1]")
        if not (0.0 <= self.turing_threshold <= 1.0):
            raise ValueError("turing_threshold must be in [0, 1]")
        if not (0.0 <= self.jitter_var <= 0.01):
            raise ValueError("jitter_var must be in [0, 0.01]")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize configuration to a dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "grid_size": self.grid_size,
            "steps": self.steps,
            "alpha": self.alpha,
            "spike_probability": self.spike_probability,
            "turing_enabled": self.turing_enabled,
            "turing_threshold": self.turing_threshold,
            "quantum_jitter": self.quantum_jitter,
            "jitter_var": self.jitter_var,
            "seed": self.seed,
            "neuromodulation": self.neuromodulation.to_dict()
            if self.neuromodulation is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationConfig:
        """
        Create configuration from a dictionary.

        Args:
            data: Dictionary with configuration values.

        Returns:
            New SimulationConfig instance.
        """

        def _parse_bool(value: Any, default: bool) -> bool:
            """Parse booleans from common serialized formats.

            Supports native bools, string representations ("true"/"false"),
            and numeric 0/1 flags. Falls back to the provided default when the
            value is None or unrecognized.
            """

            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes", "y", "on"}:
                    return True
                if normalized in {"false", "0", "no", "n", "off"}:
                    return False
                return default
            if isinstance(value, (int, float)):
                return bool(value)
            return default

        seed_value = data.get("seed")

        def _parse_seed(value: Any) -> int | None:
            """Parse optional seed values from loosely-typed inputs.

            Accepts integers or numeric strings and treats empty strings or
            ``None`` as absence of a seed rather than raising an error. This
            makes the deserializer resilient to common scenarios where form
            fields or environment variables provide blank values.
            """

            if value is None:
                return None

            if isinstance(value, str):
                if value.strip() == "":
                    return None
                try:
                    return int(value)
                except ValueError as exc:
                    raise ValueError(
                        f"seed must be an integer when provided, got {value!r}"
                    ) from exc

            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"seed must be an integer when provided, got {value!r}") from exc

        return cls(
            grid_size=int(data.get("grid_size", 64)),
            steps=int(data.get("steps", 64)),
            alpha=float(data.get("alpha", 0.18)),
            spike_probability=float(data.get("spike_probability", 0.25)),
            turing_enabled=_parse_bool(data.get("turing_enabled"), True),
            turing_threshold=float(data.get("turing_threshold", 0.75)),
            quantum_jitter=_parse_bool(data.get("quantum_jitter"), False),
            jitter_var=float(data.get("jitter_var", 0.0005)),
            seed=_parse_seed(seed_value),
            neuromodulation=NeuromodulationConfig.from_dict(data["neuromodulation"])
            if data.get("neuromodulation") is not None
            else None,
        )


@dataclass
class SimulationResult:
    """
    Container for simulation output data.

    Attributes
    ----------
    field : NDArray[np.float64]
        Final 2D potential field in Volts. Shape (N, N).
    history : NDArray[np.float64] | None
        Time series of field snapshots. Shape (T, N, N). None if not stored.
    growth_events : int
        Total number of growth events during simulation.
    turing_activations : int
        Number of Turing pattern activation events during simulation.
    clamping_events : int
        Number of field clamping events during simulation.
    metadata : dict[str, Any]
        Additional simulation metadata (timing, parameters, etc.).

    Reference:
        docs/MFN_DATA_MODEL.md — Canonical data model
        docs/MFN_DATA_PIPELINES.md — Dataset schema
    """

    field: NDArray[np.float64]
    history: NDArray[np.float64] | None = None
    growth_events: int = 0
    turing_activations: int = 0
    clamping_events: int = 0
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate result data."""
        if self.field.ndim != 2:
            raise ValueError("field must be 2D array")
        if self.field.shape[0] != self.field.shape[1]:
            raise ValueError("field must be square")
        if self.history is not None:
            if self.history.ndim != 3:
                raise ValueError("history must be 3D array (T, N, N)")
            if self.history.shape[1:] != self.field.shape:
                raise ValueError("history spatial dimensions must match field")
            if not np.isfinite(self.history).all():
                raise ValueError("history contains NaN or Inf values")
        if not np.isfinite(self.field).all():
            raise ValueError("field contains NaN or Inf values")

    @property
    def grid_size(self) -> int:
        """Return the grid size N."""
        return int(self.field.shape[0])

    @property
    def has_history(self) -> bool:
        """Check if time history is available."""
        return self.history is not None

    @property
    def num_steps(self) -> int:
        """Return the number of simulated time steps represented by the result.

        Preference order:
        1. Explicit history length when available.
        2. ``steps_computed`` in metadata produced by the simulation engine.
        3. ``config['steps']`` when present in metadata.
        4. Fallback to ``0`` when no information is available.
        """
        if self.history is not None:
            return int(self.history.shape[0])

        steps_computed = self.metadata.get("steps_computed")
        if isinstance(steps_computed, (int, float)):
            return int(steps_computed)

        config_metadata = self.metadata.get("config")
        if isinstance(config_metadata, dict):
            steps_value = config_metadata.get("steps")
            if isinstance(steps_value, (int, float)):
                return int(steps_value)

        return 0

    def to_dict(self, include_arrays: bool = False) -> dict[str, Any]:
        """
        Serialize result to a dictionary.

        Args:
            include_arrays: If True, include field and history arrays as lists.
                           If False, only include metadata and statistics.

        Returns:
            Dictionary representation of the result.
        """
        result: dict[str, Any] = {
            "grid_size": self.grid_size,
            "num_steps": self.num_steps,
            "has_history": self.has_history,
            "growth_events": self.growth_events,
            "turing_activations": self.turing_activations,
            "clamping_events": self.clamping_events,
            "metadata": self.metadata.copy(),
            # Field statistics
            "field_min_mV": float(np.min(self.field)) * 1000.0,
            "field_max_mV": float(np.max(self.field)) * 1000.0,
            "field_mean_mV": float(np.mean(self.field)) * 1000.0,
            "field_std_mV": float(np.std(self.field)) * 1000.0,
        }
        if include_arrays:
            result["field"] = self.field.tolist()
            if self.history is not None:
                result["history"] = self.history.tolist()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationResult:
        """
        Create SimulationResult from a dictionary.

        Args:
            data: Dictionary with result data including 'field' array.

        Returns:
            New SimulationResult instance.

        Raises:
            KeyError: If 'field' key is missing.
            ValueError: If field data is invalid.
        """
        if "field" not in data:
            raise KeyError("'field' key is required in data dictionary")

        field = np.array(data["field"], dtype=np.float64)
        history = None
        if "history" in data and data["history"] is not None:
            history = np.array(data["history"], dtype=np.float64)

        return cls(
            field=field,
            history=history,
            growth_events=int(data.get("growth_events", 0)),
            turing_activations=int(data.get("turing_activations", 0)),
            clamping_events=int(data.get("clamping_events", 0)),
            metadata=dict(data.get("metadata", {})),
        )
