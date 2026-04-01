"""Simulation API surface for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
This module provides stable imports for the reference simulator.

References
----------
docs/SPEC.md#P2-11
"""

from __future__ import annotations

from bnsyn.sim.network import Network, NetworkParams, run_simulation

__all__ = ["Network", "NetworkParams", "run_simulation"]
