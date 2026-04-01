"""Connectivity management (sparse and dense).

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports deterministic sparse connectivity builders and metrics.

References
----------
docs/SPEC.md#P2-11
"""

from __future__ import annotations

from bnsyn.connectivity.sparse import SparseConnectivity, build_random_connectivity

__all__ = ["SparseConnectivity", "build_random_connectivity"]
