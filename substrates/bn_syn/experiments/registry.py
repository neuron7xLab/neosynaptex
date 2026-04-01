"""Experiment configuration registry.

This module defines available experiments and their configurations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExperimentConfig:
    """Configuration for a reproducible experiment.

    Attributes
    ----------
    name : str
        Unique experiment identifier.
    description : str
        Human-readable description.
    default_seeds : int
        Default number of seeds for validation runs.
    smoke_seeds : int
        Number of seeds for fast smoke tests.
    default_steps : int
        Number of consolidation steps per trial.
    params : dict[str, Any]
        Experiment-specific parameters.
    """

    name: str
    description: str
    default_seeds: int
    smoke_seeds: int
    default_steps: int
    params: dict[str, Any]


# Registry of all available experiments
EXPERIMENTS: dict[str, ExperimentConfig] = {
    "temp_ablation_v1": ExperimentConfig(
        name="temp_ablation_v1",
        description="Temperature ablation: cooling vs fixed vs random temperature regimes",
        default_seeds=20,
        smoke_seeds=5,
        default_steps=5000,
        params={
            "T0": 1.0,
            "Tmin": 1e-3,
            "alpha": 0.95,
            "Tc": 0.1,
            "gate_tau": 0.02,
            "dt_s": 1.0,  # Larger timestep for faster consolidation
            "pulse_amplitude": 2.0,  # Stronger pulses
            "pulse_prob": 0.05,  # More frequent pulses
        },
    ),
    "temp_ablation_v2": ExperimentConfig(
        name="temp_ablation_v2",
        description="Temperature ablation v2: piecewise cooling with warmup to preserve consolidation",
        default_seeds=20,
        smoke_seeds=5,
        default_steps=5000,
        params={
            "T0": 1.0,
            "Tmin": 1e-3,
            "alpha": 0.9995,  # Slow cooling to maintain consolidation
            "Tc": 0.1,
            "gate_tau": 0.02,
            "warmup_steps": 500,  # Hold T=T0 before cooling
            "matrix_size": (10, 10),  # Explicit synapse matrix dimensions
            "dt_s": 1.0,
            "pulse_amplitude": 2.0,
            "pulse_prob": 0.05,
        },
    ),
}


def get_experiment_config(name: str) -> ExperimentConfig:
    """Retrieve experiment configuration by name.

    Parameters
    ----------
    name : str
        Experiment identifier.

    Returns
    -------
    ExperimentConfig
        Experiment configuration.

    Raises
    ------
    KeyError
        If experiment name is not found in registry.
    """
    if name not in EXPERIMENTS:
        available = ", ".join(EXPERIMENTS.keys())
        raise KeyError(f"Unknown experiment: {name}. Available: {available}")
    return EXPERIMENTS[name]
