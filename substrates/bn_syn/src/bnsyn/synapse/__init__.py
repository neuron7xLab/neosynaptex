"""Synapse dynamics subpackage.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides conductance-based synapse state and update routines.

References
----------
docs/SPEC.md#P0-2
"""

from .conductance import (
    ConductanceState as ConductanceState,
    ConductanceSynapses as ConductanceSynapses,
)

__all__ = ["ConductanceState", "ConductanceSynapses"]
