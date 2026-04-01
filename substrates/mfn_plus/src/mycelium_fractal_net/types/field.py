"""
Field state and canonical simulation surface types for MyceliumFractalNet.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from mycelium_fractal_net.types.detection import AnomalyEvent
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.forecast import ComparisonResult, ForecastResult


class BoundaryCondition(str, Enum):
    PERIODIC = "periodic"
    NEUMANN = "neumann"
    DIRICHLET = "dirichlet"


@dataclass(frozen=True)
class GridShape:
    rows: int
    cols: int

    def __post_init__(self) -> None:
        if self.rows < 2:
            raise ValueError(f"rows must be >= 2, got {self.rows}")
        if self.cols < 2:
            raise ValueError(f"cols must be >= 2, got {self.cols}")

    @property
    def is_square(self) -> bool:
        return self.rows == self.cols

    @property
    def size(self) -> int:
        if not self.is_square:
            raise ValueError("size only defined for square grids")
        return self.rows

    @property
    def total_cells(self) -> int:
        return self.rows * self.cols

    def to_tuple(self) -> tuple[int, int]:
        return (self.rows, self.cols)

    @classmethod
    def square(cls, size: int) -> GridShape:
        return cls(rows=size, cols=size)


@dataclass
class FieldState:
    data: NDArray[np.float64]
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data, dtype=np.float64)
        if self.data.ndim != 2:
            raise ValueError(f"data must be 2D, got {self.data.ndim}D")
        if self.data.shape[0] < 2 or self.data.shape[1] < 2:
            raise ValueError(f"grid dimensions must be >= 2, got {self.data.shape}")
        if not np.isfinite(self.data).all():
            raise ValueError("data contains NaN or Inf values")

    @property
    def shape(self) -> GridShape:
        return GridShape(rows=self.data.shape[0], cols=self.data.shape[1])

    @property
    def grid_size(self) -> int:
        if self.data.shape[0] != self.data.shape[1]:
            raise ValueError("grid_size only defined for square fields")
        return int(self.data.shape[0])

    @property
    def min_mV(self) -> float:
        return float(np.min(self.data)) * 1000.0

    @property
    def max_mV(self) -> float:
        return float(np.max(self.data)) * 1000.0

    @property
    def mean_mV(self) -> float:
        return float(np.mean(self.data)) * 1000.0

    @property
    def std_mV(self) -> float:
        return float(np.std(self.data)) * 1000.0

    def to_binary(self, threshold_v: float = -0.060) -> NDArray[np.bool_]:
        return self.data > threshold_v

    def to_dict(self) -> dict[str, Any]:
        return {
            "shape": self.shape.to_tuple(),
            "boundary": self.boundary.value,
            "min_mV": self.min_mV,
            "max_mV": self.max_mV,
            "mean_mV": self.mean_mV,
            "std_mV": self.std_mV,
        }


@dataclass
class FieldHistory:
    data: NDArray[np.float64]
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data, dtype=np.float64)
        if self.data.ndim != 3:
            raise ValueError(f"data must be 3D (T, N, M), got {self.data.ndim}D")
        if self.data.shape[0] < 1:
            raise ValueError(f"time steps must be >= 1, got {self.data.shape[0]}")
        if self.data.shape[1] < 2 or self.data.shape[2] < 2:
            raise ValueError(f"spatial dimensions must be >= 2, got {self.data.shape[1:]}")
        if not np.isfinite(self.data).all():
            raise ValueError("data contains NaN or Inf values")

    @property
    def num_steps(self) -> int:
        return int(self.data.shape[0])

    @property
    def spatial_shape(self) -> GridShape:
        return GridShape(rows=self.data.shape[1], cols=self.data.shape[2])

    @property
    def grid_size(self) -> int:
        if self.data.shape[1] != self.data.shape[2]:
            raise ValueError("grid_size only defined for square fields")
        return int(self.data.shape[1])

    def get_frame(self, t: int) -> FieldState:
        if t < 0 or t >= self.num_steps:
            raise IndexError(f"time index {t} out of range [0, {self.num_steps})")
        return FieldState(data=self.data[t].copy(), boundary=self.boundary)

    @property
    def initial_state(self) -> FieldState:
        return self.get_frame(0)

    @property
    def final_state(self) -> FieldState:
        return self.get_frame(self.num_steps - 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_steps": self.num_steps,
            "spatial_shape": self.spatial_shape.to_tuple(),
            "boundary": self.boundary.value,
            "initial_min_mV": self.initial_state.min_mV,
            "initial_max_mV": self.initial_state.max_mV,
            "final_min_mV": self.final_state.min_mV,
            "final_max_mV": self.final_state.max_mV,
        }


@dataclass(frozen=True)
class GABAATonicSpec:
    profile: str = "baseline_nominal"
    agonist_concentration_um: float = 0.0
    resting_affinity_um: float = 0.0
    active_affinity_um: float = 0.0
    desensitization_rate_hz: float = 0.0
    recovery_rate_hz: float = 0.0
    shunt_strength: float = 0.0
    rest_offset_mv: float = 0.0
    baseline_activation_offset_mv: float = 0.0
    tonic_inhibition_scale: float = 1.0
    k_on: float = 0.0
    k_off: float = 0.0
    K_R: float = 0.0
    c: float = 1.0
    Q: float = 1.0
    L: float = 1.0
    binding_sites: int = 1
    k_leak_reduction_fraction: float = 0.0

    def __post_init__(self) -> None:
        if self.binding_sites < 1:
            raise ValueError("binding_sites must be >= 1")
        if not (0.0 <= self.shunt_strength <= 1.0):
            raise ValueError("shunt_strength must be in [0, 1]")
        if self.tonic_inhibition_scale < 0.0:
            raise ValueError("tonic_inhibition_scale must be >= 0")
        if not (0.0 <= self.k_leak_reduction_fraction <= 1.0):
            raise ValueError("k_leak_reduction_fraction must be in [0, 1]")
        if self.c <= 0.0 or self.Q <= 0.0 or self.L <= 0.0:
            raise ValueError("c, Q, and L must be > 0")

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GABAATonicSpec:
        return cls(**{name: data[name] for name in cls.__dataclass_fields__ if name in data})


@dataclass(frozen=True)
class SerotonergicPlasticitySpec:
    profile: str = "baseline_nominal"
    gain_fluidity_coeff: float = 0.0
    reorganization_drive: float = 0.0
    coherence_bias: float = 0.0
    plasticity_scale: float = 1.0
    connectivity_flattening_scale: float = 0.0
    complexity_gain_scale: float = 0.0

    def __post_init__(self) -> None:
        if self.plasticity_scale < 0.0:
            raise ValueError("plasticity_scale must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SerotonergicPlasticitySpec:
        return cls(**{name: data[name] for name in cls.__dataclass_fields__ if name in data})


@dataclass(frozen=True)
class ObservationNoiseSpec:
    profile: str = "baseline_nominal"
    std: float = 0.0
    temporal_smoothing: float = 0.0

    def __post_init__(self) -> None:
        if self.std < 0.0:
            raise ValueError("observation noise std must be >= 0")
        if not (0.0 <= self.temporal_smoothing <= 1.0):
            raise ValueError("temporal_smoothing must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObservationNoiseSpec:
        return cls(**{name: data[name] for name in cls.__dataclass_fields__ if name in data})


@dataclass(frozen=True)
class NeuromodulationSpec:
    profile: str = "baseline_nominal"
    profile_id: str = "baseline_nominal"
    evidence_version: str = "mfn-neuromod-evidence-v2"
    enabled: bool = False
    dt_seconds: float = 1.0
    intrinsic_field_jitter: bool = False
    intrinsic_field_jitter_var: float = 0.0005
    baseline_activation_offset_mv: float = 0.0
    tonic_inhibition_scale: float = 1.0
    gain_fluidity_coeff: float = 0.0
    gabaa_tonic: GABAATonicSpec | None = None
    serotonergic: SerotonergicPlasticitySpec | None = None
    observation_noise: ObservationNoiseSpec | None = None

    def __post_init__(self) -> None:
        if self.dt_seconds <= 0.0:
            raise ValueError("neuromodulation.dt_seconds must be > 0")
        if not (0.0 <= self.intrinsic_field_jitter_var <= 0.01):
            raise ValueError("neuromodulation.intrinsic_field_jitter_var must be in [0, 0.01]")
        if self.tonic_inhibition_scale < 0.0:
            raise ValueError("neuromodulation.tonic_inhibition_scale must be >= 0")
        if self.profile_id == "baseline_nominal" and self.profile:
            object.__setattr__(self, "profile_id", self.profile)
        if self.gabaa_tonic is not None:
            if (
                self.tonic_inhibition_scale == 1.0
                and self.gabaa_tonic.tonic_inhibition_scale != 1.0
            ):
                object.__setattr__(
                    self,
                    "tonic_inhibition_scale",
                    float(self.gabaa_tonic.tonic_inhibition_scale),
                )
            if (
                self.baseline_activation_offset_mv == 0.0
                and self.gabaa_tonic.baseline_activation_offset_mv != 0.0
            ):
                object.__setattr__(
                    self,
                    "baseline_activation_offset_mv",
                    float(self.gabaa_tonic.baseline_activation_offset_mv),
                )
        if (
            self.serotonergic is not None
            and self.gain_fluidity_coeff == 0.0
            and self.serotonergic.gain_fluidity_coeff != 0.0
        ):
            object.__setattr__(
                self,
                "gain_fluidity_coeff",
                float(self.serotonergic.gain_fluidity_coeff),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "profile_id": self.profile_id,
            "evidence_version": self.evidence_version,
            "enabled": self.enabled,
            "dt_seconds": float(self.dt_seconds),
            "intrinsic_field_jitter": self.intrinsic_field_jitter,
            "intrinsic_field_jitter_var": float(self.intrinsic_field_jitter_var),
            "baseline_activation_offset_mv": float(self.baseline_activation_offset_mv),
            "tonic_inhibition_scale": float(self.tonic_inhibition_scale),
            "gain_fluidity_coeff": float(self.gain_fluidity_coeff),
            "gabaa_tonic": (None if self.gabaa_tonic is None else self.gabaa_tonic.to_dict()),
            "serotonergic": (None if self.serotonergic is None else self.serotonergic.to_dict()),
            "observation_noise": (
                None if self.observation_noise is None else self.observation_noise.to_dict()
            ),
        }

    @classmethod
    def from_profile(cls, profile: str) -> NeuromodulationSpec:
        from mycelium_fractal_net.neurochem.profiles import get_profile

        return cls.from_dict(get_profile(profile))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NeuromodulationSpec:
        from mycelium_fractal_net.neurochem.profiles import (
            PROFILE_REGISTRY,
            get_profile,
        )

        clean = dict(data)
        profile_name = str(clean.get("profile", clean.get("profile_id", "baseline_nominal")))
        if profile_name in PROFILE_REGISTRY:
            merged = get_profile(profile_name)
            for key, value in clean.items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    merged[key].update(value)
                else:
                    merged[key] = value
            clean = merged
        clean["gabaa_tonic"] = (
            None
            if clean.get("gabaa_tonic") is None
            else GABAATonicSpec.from_dict(clean["gabaa_tonic"])
        )
        clean["serotonergic"] = (
            None
            if clean.get("serotonergic") is None
            else SerotonergicPlasticitySpec.from_dict(clean["serotonergic"])
        )
        clean["observation_noise"] = (
            None
            if clean.get("observation_noise") is None
            else ObservationNoiseSpec.from_dict(clean["observation_noise"])
        )
        return cls(**{name: clean[name] for name in cls.__dataclass_fields__ if name in clean})


@dataclass(frozen=True)
class SimulationSpec:
    grid_size: int = 64
    steps: int = 64
    alpha: float = 0.18
    spike_probability: float = 0.25
    turing_enabled: bool = True
    turing_threshold: float = 0.75
    quantum_jitter: bool = False
    jitter_var: float = 0.0005
    seed: int | None = None
    neuromodulation: NeuromodulationSpec | None = None

    def __post_init__(self) -> None:
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

    def as_runtime_dict(self) -> dict[str, Any]:
        return {
            "grid_size": int(self.grid_size),
            "steps": int(self.steps),
            "alpha": float(self.alpha),
            "spike_probability": float(self.spike_probability),
            "turing_enabled": bool(self.turing_enabled),
            "turing_threshold": float(self.turing_threshold),
            "quantum_jitter": bool(self.quantum_jitter),
            "jitter_var": float(self.jitter_var),
            "seed": self.seed,
            "neuromodulation": (
                None if self.neuromodulation is None else self.neuromodulation.to_dict()
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.as_runtime_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationSpec:
        def _parse_bool(value: Any, default: bool) -> bool:
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
        if seed_value in (None, ""):
            seed: int | None = None
        else:
            seed = int(seed_value)  # type: ignore[arg-type]
        neuromod_raw = data.get("neuromodulation")
        neuromod = None if neuromod_raw is None else NeuromodulationSpec.from_dict(neuromod_raw)
        return cls(
            grid_size=int(data.get("grid_size", 64)),
            steps=int(data.get("steps", 64)),
            alpha=float(data.get("alpha", 0.18)),
            spike_probability=float(data.get("spike_probability", 0.25)),
            turing_enabled=_parse_bool(data.get("turing_enabled"), True),
            turing_threshold=float(data.get("turing_threshold", 0.75)),
            quantum_jitter=_parse_bool(data.get("quantum_jitter"), False),
            jitter_var=float(data.get("jitter_var", 0.0005)),
            seed=seed,
            neuromodulation=neuromod,
        )


@dataclass(frozen=True)
class NeuromodulationStateSnapshot:
    """Strongly-typed snapshot of neuromodulation state at end of simulation.

    Replaces the untyped metadata['neuromodulation_state'] dict.
    All fields correspond to NeuromodulationState outputs.
    """

    occupancy_resting: float = 1.0
    occupancy_active: float = 0.0
    occupancy_desensitized: float = 0.0
    effective_inhibition: float = 0.0
    effective_gain: float = 0.0
    plasticity_index: float = 0.0
    observation_noise_gain: float = 0.0
    excitability_offset_v: float = 0.0

    def __post_init__(self) -> None:
        # Occupancy must sum to ~1.0 (within floating point tolerance)
        total = self.occupancy_resting + self.occupancy_active + self.occupancy_desensitized
        if abs(total - 1.0) > 1e-4:
            raise ValueError(
                f"Occupancy fractions must sum to ~1.0, got {total:.6f} "
                f"(resting={self.occupancy_resting}, active={self.occupancy_active}, "
                f"desensitized={self.occupancy_desensitized})"
            )
        if not (0.0 <= self.occupancy_resting <= 1.0):
            raise ValueError(f"occupancy_resting must be in [0, 1], got {self.occupancy_resting}")
        if not (0.0 <= self.occupancy_active <= 1.0):
            raise ValueError(f"occupancy_active must be in [0, 1], got {self.occupancy_active}")
        if not (0.0 <= self.occupancy_desensitized <= 1.0):
            raise ValueError(
                f"occupancy_desensitized must be in [0, 1], got {self.occupancy_desensitized}"
            )
        if self.effective_inhibition < 0.0:
            raise ValueError(f"effective_inhibition must be >= 0, got {self.effective_inhibition}")

    def to_dict(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NeuromodulationStateSnapshot:
        return cls(**{k: float(data[k]) for k in cls.__dataclass_fields__ if k in data})


@dataclass(frozen=True)
class FieldSequence:
    field: NDArray[np.float64]
    history: NDArray[np.float64] | None = None
    spec: SimulationSpec | None = None
    neuromodulation_state: NeuromodulationStateSnapshot | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        field = np.asanyarray(self.field, dtype=np.float64)
        object.__setattr__(self, "field", field)
        if field.ndim != 2:
            raise ValueError(f"field must be 2D, got {field.ndim}D")
        if field.shape[0] < 2 or field.shape[1] < 2:
            raise ValueError(f"grid dimensions must be >= 2, got {field.shape}")
        if not np.isfinite(field).all():
            raise ValueError("field contains NaN or Inf values")

        history = self.history
        if history is not None:
            history = np.asanyarray(history, dtype=np.float64)
            if history.ndim != 3:
                raise ValueError(f"history must be 3D, got {history.ndim}D")
            if history.shape[1:] != field.shape:
                raise ValueError("history spatial dimensions must match field")
            if not np.isfinite(history).all():
                raise ValueError("history contains NaN or Inf values")
            object.__setattr__(self, "history", history)

        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    @property
    def field_min_mV(self) -> float:
        return float(np.min(self.field)) * 1000

    @property
    def field_max_mV(self) -> float:
        return float(np.max(self.field)) * 1000

    @property
    def field_mean_mV(self) -> float:
        return float(np.mean(self.field)) * 1000

    def __repr__(self) -> str:
        n = self.field.shape[0]
        seed = self.spec.seed if self.spec else "?"
        neuro = ""
        if self.spec and self.spec.neuromodulation and self.spec.neuromodulation.enabled:
            neuro = f", neuromod={self.spec.neuromodulation.profile}"
        return (
            f"FieldSequence({n}x{n}, {self.num_steps} steps, "
            f"[{self.field_min_mV:.1f}, {self.field_max_mV:.1f}] mV, seed={seed}{neuro})"
        )

    @property
    def grid_size(self) -> int:
        if self.field.shape[0] != self.field.shape[1]:
            raise ValueError("grid_size only defined for square fields")
        return int(self.field.shape[0])

    @property
    def num_steps(self) -> int:
        if self.history is not None:
            return int(self.history.shape[0])
        if self.spec is not None:
            return int(self.spec.steps)
        if isinstance(self.metadata, dict) and isinstance(self.metadata.get("steps"), (int, float)):
            return int(self.metadata["steps"])
        return 1

    @property
    def has_history(self) -> bool:
        return self.history is not None

    @property
    def runtime_hash(self) -> str:
        payload = self.field.tobytes()
        if self.history is not None:
            payload += self.history.tobytes()
        return hashlib.sha256(payload).hexdigest()[:16]

    @property
    def final_state(self) -> FieldState:
        return FieldState(self.field)

    @property
    def temporal_state(self) -> FieldHistory | None:
        return None if self.history is None else FieldHistory(self.history)

    # ─── Fluent pipeline interface ───────────────────────────

    def extract(self) -> MorphologyDescriptor:
        """Extract morphology descriptor. Shorthand for mfn.extract(self)."""
        from mycelium_fractal_net.analytics.morphology import (
            compute_morphology_descriptor,
        )

        return compute_morphology_descriptor(self)

    def detect(self) -> AnomalyEvent:
        """Detect anomalies. Shorthand for mfn.detect(self)."""
        from mycelium_fractal_net.core.detect import detect_anomaly

        return detect_anomaly(self)

    def forecast(self, horizon: int = 8) -> ForecastResult:
        """Forecast future states. Shorthand for mfn.forecast(self, horizon)."""
        from mycelium_fractal_net.core.forecast import forecast_next

        return forecast_next(self, horizon=horizon)

    def compare(self, other: FieldSequence) -> ComparisonResult:
        """Compare with another sequence. Shorthand for mfn.compare(self, other)."""
        from mycelium_fractal_net.core.compare import compare

        return compare(self, other)

    def explain(self) -> Any:
        """Explain every pipeline decision with reasoning chains.

        Returns a PipelineExplanation with human-readable narratives
        for detection, regime classification, and causal verification.

        >>> seq.explain().narrate()  # full human-readable explanation
        >>> seq.explain().detection.margin_to_flip  # how close to a different label
        """
        from mycelium_fractal_net.core.causal_validation import (
            validate_causal_consistency,
        )
        from mycelium_fractal_net.core.detect import detect_anomaly
        from mycelium_fractal_net.core.explainability import explain_pipeline

        event = detect_anomaly(self)
        causal = validate_causal_consistency(self, detection=event)
        return explain_pipeline(event, causal=causal)

    def stabilize(
        self,
        target_regime: str = "stable",
        allowed_levers: list[str] | None = None,
        budget: float = 10.0,
    ) -> Any:
        """Plan an intervention to stabilize this system.

        Shorthand for mfn.plan_intervention(self, ...).

        >>> plan = seq.stabilize()
        >>> print(plan.best_candidate)
        """
        from mycelium_fractal_net.intervention import plan_intervention

        return plan_intervention(
            self,
            target_regime=target_regime,
            allowed_levers=allowed_levers,
            budget=budget,
        )

    # ─────────────────────────────────────────────────────────

    def to_dict(self, include_arrays: bool = False) -> dict[str, Any]:
        spec_dict = None if self.spec is None else self.spec.to_dict()
        config_basis = spec_dict or {
            "grid_size": self.grid_size,
            "steps": self.num_steps,
        }
        config_hash = hashlib.sha256(
            json.dumps(config_basis, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        data = {
            "schema_version": "mfn-field-sequence-v1",
            "engine_version": "0.1.0",
            "grid_size": self.grid_size,
            "num_steps": self.num_steps,
            "has_history": self.has_history,
            "runtime_hash": self.runtime_hash,
            "config_hash": config_hash,
            "spec": spec_dict,
            "metadata": dict(self.metadata or {}),
            "field_min_mV": float(np.min(self.field) * 1000.0),
            "field_max_mV": float(np.max(self.field) * 1000.0),
            "field_mean_mV": float(np.mean(self.field) * 1000.0),
            "field_std_mV": float(np.std(self.field) * 1000.0),
        }
        if include_arrays:
            data["field"] = self.field.tolist()
            data["history"] = None if self.history is None else self.history.tolist()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldSequence:
        if "field" not in data:
            raise ValueError(
                "FieldSequence.from_dict requires 'field' when include_arrays=True payload is used"
            )
        field = np.asarray(data["field"], dtype=np.float64)
        history_raw = data.get("history")
        history = None if history_raw is None else np.asarray(history_raw, dtype=np.float64)
        spec_raw = data.get("spec")
        spec = None if spec_raw is None else SimulationSpec.from_dict(spec_raw)
        return cls(
            field=field,
            history=history,
            spec=spec,
            metadata=dict(data.get("metadata", {})),
        )

    def save_arrays(self, directory: str | Path) -> dict[str, str]:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        field_path = directory / "field.npy"
        np.save(field_path, self.field)
        outputs = {"field": str(field_path)}
        if self.history is not None:
            history_path = directory / "history.npy"
            np.save(history_path, self.history)
            outputs["history"] = str(history_path)
        return outputs

    @classmethod
    def from_arrays(
        cls,
        field: NDArray[np.float64],
        history: NDArray[np.float64] | None = None,
        spec: SimulationSpec | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FieldSequence:
        return cls(
            field=np.asarray(field, dtype=np.float64),
            history=None if history is None else np.asarray(history, dtype=np.float64),
            spec=spec,
            metadata=metadata,
        )
