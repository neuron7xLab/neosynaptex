"""Simulation entry points for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports the reference Network model and simulation runner.

References
----------
docs/SPEC.md
"""

from .network import (
    Network as Network,
    NetworkParams as NetworkParams,
    run_simulation as run_simulation,
)

__all__ = ["Network", "NetworkParams", "run_simulation"]
