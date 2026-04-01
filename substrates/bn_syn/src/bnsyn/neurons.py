"""Neuron dynamics API surface for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
This module provides a stable import surface that mirrors ``bnsyn.neuron``.

References
----------
docs/SPEC.md#P0-1
"""

from __future__ import annotations

from bnsyn.neuron.adex import (
    AdExState,
    IntegrationMetrics,
    adex_step,
    adex_step_adaptive,
    adex_step_with_error_tracking,
)

__all__ = [
    "AdExState",
    "IntegrationMetrics",
    "adex_step",
    "adex_step_adaptive",
    "adex_step_with_error_tracking",
]
