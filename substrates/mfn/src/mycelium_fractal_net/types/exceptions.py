"""
Custom exception classes for numerical stability and validation errors.

These exceptions provide clear error reporting for:
- Numerical instability (NaN, Inf, divergence)
- Values outside physically/logically valid ranges
- Stability constraint violations

Reference: MFN_MATH_MODEL.md Section 4.3 (Clamping and Bounds)
"""

from __future__ import annotations

from typing import Any


class StabilityError(Exception):
    """
    Raised when a numerical computation becomes unstable.

    This includes:
    - NaN or Inf values detected after integration steps
    - Violation of CFL stability conditions
    - Divergent trajectories in dynamical systems

    Attributes
    ----------
    message : str
        Human-readable error description.
    step : int | None
        The integration step at which instability was detected.
    value : Any | None
        The problematic value that triggered the error.
    """

    def __init__(
        self,
        message: str,
        step: int | None = None,
        value: Any = None,
    ) -> None:
        self.step = step
        self.value = value
        details = []
        if step is not None:
            details.append(f"step={step}")
        if value is not None:
            details.append(f"value={value}")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{detail_str}")


class ValueOutOfRangeError(Exception):
    """
    Raised when a value exceeds physically/logically allowed bounds.

    Reference bounds from MFN_MATH_MODEL.md:
    - Membrane potential: [-95, 40] mV
    - Ion concentration: > 1e-6 M (ION_CLAMP_MIN)
    - Activator/Inhibitor: [0, 1]
    - IFS scale factor: [0.2, 0.5]
    - Diffusion coefficient: < 0.25 (CFL condition)

    Attributes
    ----------
    message : str
        Human-readable error description.
    value : float | None
        The out-of-range value.
    min_bound : float | None
        The minimum allowed value.
    max_bound : float | None
        The maximum allowed value.
    parameter_name : str | None
        Name of the parameter that is out of range.
    """

    def __init__(
        self,
        message: str,
        value: float | None = None,
        min_bound: float | None = None,
        max_bound: float | None = None,
        parameter_name: str | None = None,
    ) -> None:
        self.value = value
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.parameter_name = parameter_name

        details = []
        if parameter_name is not None:
            details.append(f"parameter='{parameter_name}'")
        if value is not None:
            details.append(f"value={value}")
        if min_bound is not None:
            details.append(f"min={min_bound}")
        if max_bound is not None:
            details.append(f"max={max_bound}")

        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{detail_str}")


class NumericalInstabilityError(StabilityError):
    """
    Raised specifically for NaN or Inf values in computations.

    This is a specialized StabilityError for cases where
    floating-point arithmetic produces undefined results.

    Attributes
    ----------
    field_name : str | None
        Name of the field/array containing NaN/Inf.
    nan_count : int | None
        Number of NaN values detected.
    inf_count : int | None
        Number of Inf values detected.
    """

    def __init__(
        self,
        message: str,
        step: int | None = None,
        field_name: str | None = None,
        nan_count: int | None = None,
        inf_count: int | None = None,
    ) -> None:
        self.field_name = field_name
        self.nan_count = nan_count
        self.inf_count = inf_count

        details = []
        if field_name is not None:
            details.append(f"field='{field_name}'")
        if nan_count is not None:
            details.append(f"nan_count={nan_count}")
        if inf_count is not None:
            details.append(f"inf_count={inf_count}")

        detail_str = f" [{', '.join(details)}]" if details else ""
        super().__init__(f"{message}{detail_str}", step=step)
