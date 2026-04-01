"""Temperature scheduling and plasticity gating.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports temperature schedule utilities for consolidation control.

References
----------
docs/SPEC.md#P1-5
"""

from .schedule import TemperatureSchedule as TemperatureSchedule, gate_sigmoid as gate_sigmoid

__all__ = ["TemperatureSchedule", "gate_sigmoid"]
