"""Neuron dynamics subpackage.

Parameters
----------
None

Returns
-------
None

Notes
-----
Re-exports AdEx state and integration helpers for external API consumers.

References
----------
docs/SPEC.md#P0-1
"""

from .adex import (
    AdExState as AdExState,
    IntegrationMetrics as IntegrationMetrics,
    adex_step as adex_step,
    adex_step_with_error_tracking as adex_step_with_error_tracking,
)

__all__ = ["AdExState", "IntegrationMetrics", "adex_step", "adex_step_with_error_tracking"]
