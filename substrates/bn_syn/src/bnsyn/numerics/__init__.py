"""Numerical integration helpers for deterministic updates.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports integration helpers used by neuron and synapse dynamics.

References
----------
docs/SPEC.md
"""

from .integrators import (
    clamp_exp_arg as clamp_exp_arg,
    euler_step as euler_step,
    exp_decay_step as exp_decay_step,
    rk2_step as rk2_step,
)
from .time import compute_steps_exact as compute_steps_exact

__all__ = ["euler_step", "rk2_step", "exp_decay_step", "clamp_exp_arg", "compute_steps_exact"]
