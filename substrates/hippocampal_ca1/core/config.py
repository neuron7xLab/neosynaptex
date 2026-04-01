"""
Configuration Management for Hippocampal CA1-LAM.

This module provides:
1. YAML/JSON configuration loading and validation
2. Integration with biophysical_parameters.py
3. Configuration schema validation using contracts
4. Reproducible experiment configuration with seed management

Usage:
    from core.config import load_config, validate_config

    config = load_config("configs/experiment.yaml")
    errors = validate_config(config)
    if not errors:
        sim_config = config.core.to_simulation_config()
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

from .contracts import SimulationConfig


@dataclass
class CoreConfig:
    """
    Core configuration for CA1-LAM simulations.

    Provides a subset of essential parameters that are commonly
    varied across experiments, with sensible defaults.
    """

    # Simulation parameters
    n_neurons: int = 100
    dt: float = 0.1  # ms
    duration_ms: float = 1000.0
    seed: int = 42

    # Network parameters
    n_layers: int = 4
    connection_probability: float = 0.1

    # Weight bounds
    weight_min: float = 0.01
    weight_max: float = 10.0
    spectral_radius_target: float = 0.95

    # Plasticity parameters
    learning_rate: float = 0.001
    weight_decay: float = 1e-5

    # Theta rhythm
    theta_frequency: float = 8.0  # Hz

    # Debug/runtime options
    debug_mode: bool = True
    guards_enabled: bool = True

    def to_simulation_config(self) -> SimulationConfig:
        """Convert to SimulationConfig contract."""
        return SimulationConfig(
            n_neurons=self.n_neurons,
            dt=self.dt,
            seed=self.seed,
            duration_ms=self.duration_ms,
            weight_min=self.weight_min,
            weight_max=self.weight_max,
            debug_mode=self.debug_mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoreConfig":
        """Create from dictionary."""
        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


@dataclass
class ExperimentConfig:
    """
    Complete experiment configuration.

    Combines core config with experiment-specific metadata.
    """

    # Experiment metadata
    name: str = "default"
    description: str = ""
    version: str = "1.0.0"

    # Core configuration
    core: CoreConfig = field(default_factory=CoreConfig)

    # Optional overrides for biophysical parameters
    overrides: Dict[str, Any] = field(default_factory=dict)

    # Output configuration
    output_dir: str = "outputs"
    save_checkpoints: bool = True
    checkpoint_interval: int = 100  # timesteps

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "core": self.core.to_dict(),
            "overrides": self.overrides,
            "output_dir": self.output_dir,
            "save_checkpoints": self.save_checkpoints,
            "checkpoint_interval": self.checkpoint_interval,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentConfig":
        """Create from dictionary."""
        core_data = data.get("core", {})
        core = CoreConfig.from_dict(core_data)

        return cls(
            name=data.get("name", "default"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            core=core,
            overrides=data.get("overrides", {}),
            output_dir=data.get("output_dir", "outputs"),
            save_checkpoints=data.get("save_checkpoints", True),
            checkpoint_interval=data.get("checkpoint_interval", 100),
        )


def load_config(path: Union[str, Path]) -> ExperimentConfig:
    """
    Load configuration from YAML or JSON file.

    Args:
        path: Path to configuration file (.yaml, .yml, or .json)

    Returns:
        ExperimentConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If file format is unsupported
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                "PyYAML is required for YAML config files. " "Install with: pip install pyyaml"
            ) from e

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

    elif suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    else:
        raise ValueError(f"Unsupported config format: {suffix}. Use .yaml, .yml, or .json")

    return ExperimentConfig.from_dict(data or {})


def save_config(config: ExperimentConfig, path: Union[str, Path]) -> None:
    """
    Save configuration to YAML or JSON file.

    Args:
        config: ExperimentConfig to save
        path: Output path (.yaml, .yml, or .json)
    """
    path = Path(path)
    suffix = path.suffix.lower()

    data = config.to_dict()

    # Ensure output directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                "PyYAML is required for YAML config files. " "Install with: pip install pyyaml"
            ) from e

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    elif suffix == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    else:
        raise ValueError(f"Unsupported config format: {suffix}. Use .yaml, .yml, or .json")


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Config validation failed: {'; '.join(errors)}")


def validate_config(config: ExperimentConfig) -> List[str]:
    """
    Validate configuration for consistency and correctness.

    Args:
        config: Configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []
    core = config.core

    # Validate positive values
    if core.n_neurons <= 0:
        errors.append(f"n_neurons must be positive, got {core.n_neurons}")

    if core.dt <= 0:
        errors.append(f"dt must be positive, got {core.dt}")

    if core.duration_ms <= 0:
        errors.append(f"duration_ms must be positive, got {core.duration_ms}")

    # Validate ranges
    if not (0 < core.connection_probability <= 1):
        errors.append(
            f"connection_probability must be in (0, 1], " f"got {core.connection_probability}"
        )

    if not (0 < core.spectral_radius_target < 1):
        errors.append(
            f"spectral_radius_target must be in (0, 1), " f"got {core.spectral_radius_target}"
        )

    # Validate weight bounds
    if core.weight_min >= core.weight_max:
        errors.append(
            f"weight_min ({core.weight_min}) must be < " f"weight_max ({core.weight_max})"
        )

    if core.weight_min < 0:
        errors.append(f"weight_min must be non-negative, got {core.weight_min}")

    # Validate theta frequency
    if not (1 <= core.theta_frequency <= 20):
        errors.append(f"theta_frequency should be in [1, 20] Hz, " f"got {core.theta_frequency}")

    # Validate n_layers
    if core.n_layers not in (2, 3, 4):
        errors.append(f"n_layers must be 2, 3, or 4, got {core.n_layers}")

    return errors


def get_default_config() -> ExperimentConfig:
    """Get default experiment configuration."""
    return ExperimentConfig(
        name="default",
        description="Default CA1-LAM configuration",
    )


def create_deterministic_config(
    seed: int = 42,
    n_neurons: int = 100,
    duration_ms: float = 1000.0,
) -> ExperimentConfig:
    """
    Create a deterministic experiment configuration.

    This is useful for reproducible experiments and testing.

    Args:
        seed: Random seed for reproducibility
        n_neurons: Number of neurons
        duration_ms: Simulation duration in milliseconds

    Returns:
        ExperimentConfig with deterministic settings
    """
    return ExperimentConfig(
        name=f"deterministic_seed{seed}",
        description="Deterministic configuration for reproducibility",
        core=CoreConfig(
            n_neurons=n_neurons,
            duration_ms=duration_ms,
            seed=seed,
            debug_mode=True,
            guards_enabled=True,
        ),
    )


def merge_configs(
    base: ExperimentConfig,
    override: Dict[str, Any],
) -> ExperimentConfig:
    """
    Merge override values into base configuration.

    Args:
        base: Base configuration
        override: Dictionary of values to override

    Returns:
        New ExperimentConfig with merged values
    """
    base_dict = base.to_dict()

    # Deep merge
    def deep_merge(d1: Dict, d2: Dict) -> Dict:
        result = d1.copy()
        for k, v in d2.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    merged = deep_merge(base_dict, override)
    return ExperimentConfig.from_dict(merged)
