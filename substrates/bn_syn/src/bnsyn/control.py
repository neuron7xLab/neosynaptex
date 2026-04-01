"""Control-loop API surface for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
Aggregates criticality and temperature control utilities for public access.

References
----------
docs/SPEC.md#P0-4
docs/SPEC.md#P1-5
"""

from __future__ import annotations

from bnsyn.criticality.branching import BranchingEstimator, SigmaController
from bnsyn.energy.regularization import energy_cost, total_reward
from bnsyn.temperature.schedule import TemperatureSchedule, gate_sigmoid

__all__ = [
    "BranchingEstimator",
    "SigmaController",
    "TemperatureSchedule",
    "gate_sigmoid",
    "energy_cost",
    "total_reward",
]
