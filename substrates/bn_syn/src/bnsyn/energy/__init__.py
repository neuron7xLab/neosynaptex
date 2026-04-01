"""Energy regularization utilities.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports energy cost and reward shaping helpers used by control loops.

References
----------
docs/SPEC.md
"""

from .regularization import energy_cost as energy_cost, total_reward as total_reward

__all__ = ["energy_cost", "total_reward"]
