"""Plasticity subpackage for three-factor learning rules.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports STDP kernels and three-factor plasticity utilities.

References
----------
docs/SPEC.md#P0-3
"""

from .stdp import stdp_kernel
from .structural import (
    StructuralPlasticityEngine,
    StructuralPlasticityParams,
    StructuralPlasticityReport,
)
from .three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    three_factor_update,
)

__all__ = [
    "stdp_kernel",
    "EligibilityTraces",
    "NeuromodulatorTrace",
    "three_factor_update",
    "StructuralPlasticityEngine",
    "StructuralPlasticityParams",
    "StructuralPlasticityReport",
]
