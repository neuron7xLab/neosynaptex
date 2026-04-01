"""Production-oriented utilities for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
These modules are optional helpers for experiments and benchmarking. They are not required
by the core reference simulator and are kept dependency-light (NumPy-only by default).

References
----------
docs/SSOT.md
"""

from .adex import AdExNeuron, AdExParams
from .connectivity import ConnectivityConfig, build_connectivity

__all__ = [
    "AdExParams",
    "AdExNeuron",
    "ConnectivityConfig",
    "build_connectivity",
]
