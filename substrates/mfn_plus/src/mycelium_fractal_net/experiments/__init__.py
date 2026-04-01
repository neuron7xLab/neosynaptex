"""
Experiments submodule for MyceliumFractalNet.

Contains dataset generation and experimental utilities.

Reference: docs/MFN_DATASET_SPEC.md
"""

from .generate_dataset import (
    ConfigSampler,
    SweepConfig,
    generate_dataset,
    to_record,
)

__all__ = [
    "ConfigSampler",
    "SweepConfig",
    "generate_dataset",
    "to_record",
]

# Phase 3 experiment infrastructure
from .prr_export import PRRExporter, PRRReport
from .runner import ExperimentRunner, RunResult, ScenarioResult
from .scenarios import SCENARIO_HEALTHY, SCENARIO_PATHOLOGICAL, ScenarioConfig

__all__ += [
    "SCENARIO_HEALTHY",
    "SCENARIO_PATHOLOGICAL",
    "ExperimentRunner",
    "PRRExporter",
    "PRRReport",
    "RunResult",
    "ScenarioConfig",
    "ScenarioResult",
]

