from __future__ import annotations

"""Profile-based configuration loader with runtime validation and env overrides."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import (
    GRID_SIZE_MAX,
    GRID_SIZE_MIN,
    PROBABILITY_MAX,
    PROBABILITY_MIN,
    STEPS_MAX,
    STEPS_MIN,
)


class ConfigValidationError(ValueError):
    """Raised when a profile configuration violates constraints."""


@dataclass
class ValidationProfile:
    seed: int
    epochs: int
    batch_size: int
    grid_size: int
    steps: int
    device: str

    def validate(self) -> None:
        if not (GRID_SIZE_MIN <= self.grid_size <= GRID_SIZE_MAX):
            raise ConfigValidationError(
                f"grid_size must be between {GRID_SIZE_MIN} and {GRID_SIZE_MAX}"
            )
        if not (STEPS_MIN <= self.steps <= STEPS_MAX):
            raise ConfigValidationError(f"steps must be between {STEPS_MIN} and {STEPS_MAX}")
        for name in ("seed", "epochs", "batch_size"):
            if getattr(self, name) <= 0:
                raise ConfigValidationError(f"{name} must be positive")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationProfile:
        profile = cls(
            seed=int(data["seed"]),
            epochs=int(data["epochs"]),
            batch_size=int(data["batch_size"]),
            grid_size=int(data["grid_size"]),
            steps=int(data["steps"]),
            device=str(data.get("device", "cpu")),
        )
        profile.validate()
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "grid_size": self.grid_size,
            "steps": self.steps,
            "device": self.device,
        }


@dataclass
class ModelProfile:
    input_dim: int
    hidden_dim: int
    use_sparse_attention: bool
    use_stdp: bool

    def validate(self) -> None:
        if self.input_dim <= 0:
            raise ConfigValidationError("input_dim must be positive")
        if self.hidden_dim <= 0:
            raise ConfigValidationError("hidden_dim must be positive")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelProfile:
        profile = cls(
            input_dim=int(data["input_dim"]),
            hidden_dim=int(data["hidden_dim"]),
            use_sparse_attention=bool(data.get("use_sparse_attention", True)),
            use_stdp=bool(data.get("use_stdp", True)),
        )
        profile.validate()
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "use_sparse_attention": self.use_sparse_attention,
            "use_stdp": self.use_stdp,
        }


@dataclass
class SimulationProfile:
    turing_enabled: bool
    turing_threshold: float
    quantum_jitter: bool
    jitter_var: float

    def validate(self) -> None:
        if not (PROBABILITY_MIN <= self.turing_threshold <= PROBABILITY_MAX):
            raise ConfigValidationError("turing_threshold must be within [0, 1]")
        if self.jitter_var < 0:
            raise ConfigValidationError("jitter_var must be non-negative")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationProfile:
        profile = cls(
            turing_enabled=bool(data.get("turing_enabled", True)),
            turing_threshold=float(data.get("turing_threshold", 0.75)),
            quantum_jitter=bool(data.get("quantum_jitter", False)),
            jitter_var=float(data.get("jitter_var", 0.0)),
        )
        profile.validate()
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "turing_enabled": self.turing_enabled,
            "turing_threshold": self.turing_threshold,
            "quantum_jitter": self.quantum_jitter,
            "jitter_var": self.jitter_var,
        }


@dataclass
class FederatedProfile:
    num_clusters: int
    byzantine_fraction: float
    sample_fraction: float

    def validate(self) -> None:
        for name, value in (
            ("byzantine_fraction", self.byzantine_fraction),
            ("sample_fraction", self.sample_fraction),
        ):
            if not (PROBABILITY_MIN <= value <= PROBABILITY_MAX):
                raise ConfigValidationError(f"{name} must be within [0, 1]")
        if self.num_clusters <= 0:
            raise ConfigValidationError("num_clusters must be positive")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FederatedProfile:
        profile = cls(
            num_clusters=int(data.get("num_clusters", 1)),
            byzantine_fraction=float(data.get("byzantine_fraction", 0.0)),
            sample_fraction=float(data.get("sample_fraction", 1.0)),
        )
        profile.validate()
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_clusters": self.num_clusters,
            "byzantine_fraction": self.byzantine_fraction,
            "sample_fraction": self.sample_fraction,
        }


@dataclass
class ExpectedMetricsProfile:
    runtime_seconds_max: float
    memory_mb_max: float
    fractal_dim_range: tuple[float, float]
    lyapunov_max: float

    def validate(self) -> None:
        low, high = self.fractal_dim_range
        if low <= 0 or high <= 0 or low >= high:
            raise ConfigValidationError("fractal_dim_range must be (low, high) with 0 < low < high")
        if self.runtime_seconds_max <= 0:
            raise ConfigValidationError("runtime_seconds_max must be positive")
        if self.memory_mb_max <= 0:
            raise ConfigValidationError("memory_mb_max must be positive")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpectedMetricsProfile:
        profile = cls(
            runtime_seconds_max=float(data.get("runtime_seconds_max", 0)),
            memory_mb_max=float(data.get("memory_mb_max", 0)),
            fractal_dim_range=tuple(data.get("fractal_dim_range", (1.0, 2.0))),
            lyapunov_max=float(data.get("lyapunov_max", 0)),
        )
        profile.validate()
        return profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_seconds_max": self.runtime_seconds_max,
            "memory_mb_max": self.memory_mb_max,
            "fractal_dim_range": list(self.fractal_dim_range),
            "lyapunov_max": self.lyapunov_max,
        }


@dataclass
class ConfigProfile:
    name: str
    description: str
    validation: ValidationProfile
    model: ModelProfile
    simulation: SimulationProfile
    federated: FederatedProfile
    expected_metrics: ExpectedMetricsProfile

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "validation": self.validation.to_dict(),
            "model": self.model.to_dict(),
            "simulation": self.simulation.to_dict(),
            "federated": self.federated.to_dict(),
            "expected_metrics": self.expected_metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigProfile:
        required_keys = {
            "name",
            "description",
            "validation",
            "model",
            "simulation",
            "federated",
            "expected_metrics",
        }
        missing = required_keys - data.keys()
        if missing:
            raise ConfigValidationError(f"Missing keys in profile: {sorted(missing)}")

        return cls(
            name=str(data["name"]),
            description=str(data["description"]),
            validation=ValidationProfile.from_dict(dict(data["validation"])),
            model=ModelProfile.from_dict(dict(data["model"])),
            simulation=SimulationProfile.from_dict(dict(data["simulation"])),
            federated=FederatedProfile.from_dict(dict(data["federated"])),
            expected_metrics=ExpectedMetricsProfile.from_dict(dict(data["expected_metrics"])),
        )


def _parse_override_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def apply_overrides(profile: dict[str, Any], overrides: str) -> dict[str, Any]:
    updated = dict(profile)
    if not overrides.strip():
        return updated
    for clause in overrides.split(","):
        key_value = clause.strip().split("=", 1)
        if len(key_value) != 2:
            continue
        path, raw_value = key_value
        target = updated
        parts = path.split(".")
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = _parse_override_value(raw_value.strip())
    return updated


def load_config_profile(
    profile_name: str,
    base_path: Path | str = Path("configs"),
    env_var: str = "MFN_CONFIG_OVERRIDES",
) -> ConfigProfile:
    base = Path(base_path)
    profile_path = base / f"{profile_name}.json"
    raw_data = json.loads(profile_path.read_text())
    override_spec = os.getenv(env_var)
    if override_spec:
        raw_data = apply_overrides(raw_data, override_spec)
    return ConfigProfile.from_dict(raw_data)
