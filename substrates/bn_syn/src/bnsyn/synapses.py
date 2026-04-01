"""Synapse dynamics API surface for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
This module provides a stable import surface that mirrors ``bnsyn.synapse``.

References
----------
docs/SPEC.md#P0-2
"""

from __future__ import annotations

from bnsyn.synapse.conductance import ConductanceState, ConductanceSynapses, nmda_mg_block

__all__ = [
    "ConductanceState",
    "ConductanceSynapses",
    "nmda_mg_block",
]
