"""Calibration utilities for neuronal transfer functions.

Parameters
----------
None

Returns
-------
None

Notes
-----
Exports linear f-I curve fitting helpers.

References
----------
docs/SPEC.md
"""

from .accuracy_speed import (
    IntegratorCalibrationResult as IntegratorCalibrationResult,
    calibrate_integrator_accuracy_speed as calibrate_integrator_accuracy_speed,
)
from .fit import fit_fI_curve as fit_fI_curve, fit_line as fit_line

__all__ = [
    "IntegratorCalibrationResult",
    "calibrate_integrator_accuracy_speed",
    "fit_line",
    "fit_fI_curve",
]
