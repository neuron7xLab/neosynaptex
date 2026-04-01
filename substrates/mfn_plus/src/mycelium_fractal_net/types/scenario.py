"""
Scenario types for MyceliumFractalNet data pipelines.

Re-exports canonical scenario configuration types from the pipelines module.

Reference:
    - docs/MFN_DATA_PIPELINES.md — Scenario types and configurations
"""

from __future__ import annotations

# Re-export from pipelines module (single source of truth)
from mycelium_fractal_net.pipelines.scenarios import (
    ScenarioConfig,
    ScenarioType,
)

__all__ = [
    "ScenarioConfig",
    "ScenarioType",
]
