"""
Membrane Potential Engine — Nernst-Planck Electrochemistry.

Implements stable numerical schemes for membrane potential computation:
- Nernst equation for equilibrium potentials
- Explicit Euler and RK4 integration for potential dynamics
- Ion concentration clamping for numerical stability

Reference: MFN_MATH_MODEL.md Section 1 (Membrane Potentials)

Equations Implemented:
    E_X = (RT/zF) * ln([X]_out / [X]_in)   # Nernst equation

    dV/dt = f(V, I)                         # Membrane ODE (optional)

Parameters (from MFN_MATH_MODEL.md Section 1.3):
    R = 8.314 J/(mol·K)       - Gas constant
    F = 96485.33 C/mol        - Faraday constant
    T = 310 K                 - Body temperature (37°C)
    ION_CLAMP_MIN = 1e-6 M    - Minimum ion concentration

Valid Ranges:
    Membrane potential: [-150, +150] mV (physiological: [-95, +40] mV)
    Ion concentration: > 1e-6 M
    Temperature: [273, 320] K
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from .exceptions import NumericalInstabilityError, ValueOutOfRangeError

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

# === Physical Constants (SI) ===
# Reference: MFN_MATH_MODEL.md Section 1.3
# These are well-established physical constants (CODATA 2018)
R_GAS_CONSTANT: float = 8.314  # J/(mol·K) - Universal gas constant
FARADAY_CONSTANT: float = 96485.33212  # C/mol - Charge per mole electrons
BODY_TEMPERATURE_K: float = 310.0  # K (~37°C) - Mammalian body temperature

# === Biophysical Parameter Bounds ===
# Reference: MFN_MATH_MODEL.md Section 1.3
# Temperature bounds cover hypothermic to hyperthermic conditions
TEMPERATURE_MIN_K: float = 273.0  # 0°C - hypothermic limit
TEMPERATURE_MAX_K: float = 320.0  # 47°C - hyperthermic limit

# Ion valence: typical biological ions are ±1 or ±2
ION_VALENCE_ALLOWED: tuple[int, ...] = (-2, -1, 1, 2)

# Ion concentration bounds (mol/L)
# Min: 1e-6 M prevents log(0); Max: 1.0 M is extreme physiological limit
ION_CLAMP_MIN: float = 1e-6  # mol/L - prevents log(0)
ION_CONCENTRATION_MAX: float = 1.0  # mol/L - physiological upper limit

# === Numerical Stability Constants ===
# Reference: MFN_MATH_MODEL.md Section 1.6
# Membrane potential bounds based on electrochemistry limits
POTENTIAL_MIN_V: float = -0.150  # -150 mV - physical lower limit
POTENTIAL_MAX_V: float = 0.150  # +150 mV - physical upper limit
PHYSIOLOGICAL_V_MIN: float = -0.095  # -95 mV - neuronal hyperpolarization limit
PHYSIOLOGICAL_V_MAX: float = 0.040  # +40 mV - action potential peak

# Time step bounds for numerical integration
DT_MIN: float = 1e-7  # 0.1 μs - minimum sensible time step
DT_MAX: float = 1e-2  # 10 ms - maximum for stability


class IntegrationScheme(Enum):
    """Available numerical integration schemes."""

    EULER = "euler"
    RK4 = "rk4"


@dataclass
class MembraneConfig:
    """
    Configuration for membrane potential engine.

    All parameters have physically meaningful defaults derived from
    MFN_MATH_MODEL.md or are clearly marked as tunable.

    Attributes
    ----------
    temperature_k : float
        Temperature in Kelvin. Default 310 K (37°C body temperature).
    ion_clamp_min : float
        Minimum ion concentration (mol/L) for clamping. Default 1e-6.
    potential_min_v : float
        Minimum allowed membrane potential (V). Default -0.150.
    potential_max_v : float
        Maximum allowed membrane potential (V). Default +0.150.
    integration_scheme : IntegrationScheme
        Numerical scheme for ODE integration. Default Euler.
    dt : float
        Time step for integration (seconds). Default 1e-4 (0.1 ms).
    check_stability : bool
        Whether to check for NaN/Inf after each step. Default True.
    random_seed : int | None
        Seed for reproducibility. Default None (random).
    """

    temperature_k: float = BODY_TEMPERATURE_K
    ion_clamp_min: float = ION_CLAMP_MIN
    potential_min_v: float = POTENTIAL_MIN_V
    potential_max_v: float = POTENTIAL_MAX_V
    integration_scheme: IntegrationScheme = IntegrationScheme.EULER
    dt: float = 1e-4  # 0.1 ms - typical neuronal timescale
    check_stability: bool = True
    random_seed: int | None = None

    def __post_init__(self) -> None:
        """Validate configuration parameters against biophysical constraints.

        Invariants enforced:
        - Temperature: [273, 320] K (hypothermic to hyperthermic)
        - Ion clamp: > 0 (prevents log(0))
        - Time step: (0, 10 ms] for numerical stability
        - Potential bounds: min < max and within physical limits
        """
        # Temperature validation with biophysical bounds
        if not (TEMPERATURE_MIN_K <= self.temperature_k <= TEMPERATURE_MAX_K):
            raise ValueOutOfRangeError(
                f"Temperature must be in [{TEMPERATURE_MIN_K}, {TEMPERATURE_MAX_K}] K "
                "(hypothermic to hyperthermic range)",
                value=self.temperature_k,
                min_bound=TEMPERATURE_MIN_K,
                max_bound=TEMPERATURE_MAX_K,
                parameter_name="temperature_k",
            )

        # Ion clamp validation
        if self.ion_clamp_min <= 0:
            raise ValueOutOfRangeError(
                "Ion clamp minimum must be positive to prevent log(0)",
                value=self.ion_clamp_min,
                min_bound=0.0,
                parameter_name="ion_clamp_min",
            )

        # Time step validation with bounds
        if not (DT_MIN <= self.dt <= DT_MAX):
            raise ValueOutOfRangeError(
                f"Time step must be in [{DT_MIN:.0e}, {DT_MAX:.0e}] seconds "
                "for numerical stability",
                value=self.dt,
                min_bound=DT_MIN,
                max_bound=DT_MAX,
                parameter_name="dt",
            )

        # Potential range validation
        if self.potential_min_v >= self.potential_max_v:
            raise ValueOutOfRangeError(
                "potential_min_v must be less than potential_max_v",
                parameter_name="potential_min_v",
            )

        # Ensure potential bounds are within physical limits
        if self.potential_min_v < POTENTIAL_MIN_V:
            raise ValueOutOfRangeError(
                f"potential_min_v cannot be below {POTENTIAL_MIN_V * 1000:.0f} mV",
                value=self.potential_min_v,
                min_bound=POTENTIAL_MIN_V,
                parameter_name="potential_min_v",
            )
        if self.potential_max_v > POTENTIAL_MAX_V:
            raise ValueOutOfRangeError(
                f"potential_max_v cannot exceed {POTENTIAL_MAX_V * 1000:.0f} mV",
                value=self.potential_max_v,
                max_bound=POTENTIAL_MAX_V,
                parameter_name="potential_max_v",
            )


@dataclass
class MembraneMetrics:
    """
    Metrics collected during membrane potential computation.

    Useful for monitoring stability and validating results.

    Attributes
    ----------
    potential_min_v : float
        Minimum potential observed (V).
    potential_max_v : float
        Maximum potential observed (V).
    potential_mean_v : float
        Mean potential (V).
    potential_std_v : float
        Standard deviation of potential (V).
    steps_computed : int
        Number of integration steps performed.
    nan_detected : bool
        Whether NaN values were detected (and handled).
    inf_detected : bool
        Whether Inf values were detected (and handled).
    clamping_events : int
        Number of values that required clamping.
    """

    potential_min_v: float = 0.0
    potential_max_v: float = 0.0
    potential_mean_v: float = 0.0
    potential_std_v: float = 0.0
    steps_computed: int = 0
    nan_detected: bool = False
    inf_detected: bool = False
    clamping_events: int = 0


class MembraneEngine:
    """
    Engine for membrane potential computations with numerical stability.

    Implements Nernst equation and optional ODE integration for
    membrane potential dynamics.

    Reference: MFN_MATH_MODEL.md Section 1

    Example
    -------
    >>> config = MembraneConfig(temperature_k=310.0)
    >>> engine = MembraneEngine(config)
    >>> e_k = engine.compute_nernst_potential(z=1, c_out=5e-3, c_in=140e-3)
    >>> print(f"E_K = {e_k * 1000:.2f} mV")  # Expected: ~-89 mV
    """

    def __init__(self, config: MembraneConfig | None = None) -> None:
        """
        Initialize membrane engine with configuration.

        Parameters
        ----------
        config : MembraneConfig | None
            Engine configuration. If None, uses defaults.
        """
        self.config = config or MembraneConfig()
        self._metrics = MembraneMetrics()
        self._rng = np.random.default_rng(self.config.random_seed)

    @property
    def metrics(self) -> MembraneMetrics:
        """Get current metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset all metrics to initial values."""
        self._metrics = MembraneMetrics()

    def _validate_ion_valence(self, z_valence: int) -> None:
        """Validate ion valence against biophysical constraints.

        Parameters
        ----------
        z_valence : int
            Ion valence to validate.

        Raises
        ------
        ValueOutOfRangeError
            If valence is zero or not in allowed biological set.
        """
        if z_valence == 0:
            raise ValueOutOfRangeError(
                "Ion valence cannot be zero",
                value=0,
                parameter_name="z_valence",
            )
        if z_valence not in ION_VALENCE_ALLOWED:
            raise ValueOutOfRangeError(
                f"Ion valence must be one of {ION_VALENCE_ALLOWED} "
                "(biological ions: K⁺=+1, Na⁺=+1, Cl⁻=-1, Ca²⁺=+2)",
                value=float(z_valence),
                parameter_name="z_valence",
            )

    def compute_nernst_potential(
        self,
        z_valence: int,
        concentration_out_molar: float,
        concentration_in_molar: float,
        temperature_k: float | None = None,
    ) -> float:
        """
        Compute equilibrium membrane potential using Nernst equation.

        E = (RT/zF) * ln([X]_out / [X]_in)

        Reference: MFN_MATH_MODEL.md Section 1.2

        Parameters
        ----------
        z_valence : int
            Ion valence (K⁺=+1, Na⁺=+1, Cl⁻=-1, Ca²⁺=+2).
        concentration_out_molar : float
            Extracellular concentration (mol/L).
        concentration_in_molar : float
            Intracellular concentration (mol/L).
        temperature_k : float | None
            Temperature (K). Uses config default if None.

        Returns
        -------
        float
            Membrane potential in Volts.

        Raises
        ------
        ValueOutOfRangeError
            If valence is zero or not biologically valid.
        NumericalInstabilityError
            If result is NaN or Inf (should not happen with clamping).
        """
        self._validate_ion_valence(z_valence)

        temp = temperature_k if temperature_k is not None else self.config.temperature_k

        # Clamp concentrations to prevent log(0) or log(negative)
        c_out = max(concentration_out_molar, self.config.ion_clamp_min)
        c_in = max(concentration_in_molar, self.config.ion_clamp_min)

        if c_out != concentration_out_molar or c_in != concentration_in_molar:
            self._metrics.clamping_events += 1

        # Nernst equation: E = (RT/zF) * ln(c_out/c_in)
        ratio = c_out / c_in
        potential = (R_GAS_CONSTANT * temp) / (z_valence * FARADAY_CONSTANT) * math.log(ratio)

        # Stability check
        if self.config.check_stability:
            if math.isnan(potential):
                self._metrics.nan_detected = True
                raise NumericalInstabilityError(
                    "NaN in Nernst potential calculation",
                    field_name="potential",
                    nan_count=1,
                )
            if math.isinf(potential):
                self._metrics.inf_detected = True
                raise NumericalInstabilityError(
                    "Inf in Nernst potential calculation",
                    field_name="potential",
                    inf_count=1,
                )

        return potential

    def compute_nernst_potential_array(
        self,
        z_valence: int,
        concentration_out: NDArray[np.floating],
        concentration_in: NDArray[np.floating],
        temperature_k: float | None = None,
    ) -> NDArray[np.floating]:
        """
        Compute Nernst potential for arrays of concentrations.

        Vectorized version for efficiency with large datasets.

        Parameters
        ----------
        z_valence : int
            Ion valence.
        concentration_out : NDArray
            Extracellular concentrations (mol/L).
        concentration_in : NDArray
            Intracellular concentrations (mol/L).
        temperature_k : float | None
            Temperature (K).

        Returns
        -------
        NDArray
            Membrane potentials in Volts.
        """
        self._validate_ion_valence(z_valence)

        temp = temperature_k if temperature_k is not None else self.config.temperature_k

        # Clamp concentrations
        c_out = np.maximum(concentration_out, self.config.ion_clamp_min)
        c_in = np.maximum(concentration_in, self.config.ion_clamp_min)

        clamped_count = int(np.sum(c_out != concentration_out) + np.sum(c_in != concentration_in))
        self._metrics.clamping_events += clamped_count

        # Vectorized Nernst equation
        ratio = c_out / c_in
        potential = (R_GAS_CONSTANT * temp) / (z_valence * FARADAY_CONSTANT) * np.log(ratio)

        # Stability check
        if self.config.check_stability:
            nan_count = int(np.sum(np.isnan(potential)))
            inf_count = int(np.sum(np.isinf(potential)))

            if nan_count > 0:
                self._metrics.nan_detected = True
                raise NumericalInstabilityError(
                    "NaN values in Nernst potential array",
                    field_name="potential",
                    nan_count=nan_count,
                )
            if inf_count > 0:
                self._metrics.inf_detected = True
                raise NumericalInstabilityError(
                    "Inf values in Nernst potential array",
                    field_name="potential",
                    inf_count=inf_count,
                )

        # Update metrics
        self._metrics.potential_min_v = float(np.min(potential))
        self._metrics.potential_max_v = float(np.max(potential))
        self._metrics.potential_mean_v = float(np.mean(potential))
        self._metrics.potential_std_v = float(np.std(potential))

        return cast("NDArray[np.floating[Any]]", potential)

    def integrate_ode(
        self,
        v0: float | NDArray[np.floating],
        derivative_fn: Callable[[float | NDArray[np.floating]], float | NDArray[np.floating]],
        steps: int,
        clamp: bool = True,
    ) -> tuple[float | NDArray[np.floating], MembraneMetrics]:
        """
        Integrate membrane potential ODE using configured scheme.

        dV/dt = derivative_fn(V)

        Parameters
        ----------
        v0 : float | NDArray
            Initial potential(s) in Volts.
        derivative_fn : Callable
            Function computing dV/dt given V.
        steps : int
            Number of integration steps.
        clamp : bool
            Whether to clamp potential to valid range after each step.

        Returns
        -------
        tuple[float | NDArray, MembraneMetrics]
            Final potential(s) and metrics.
        """
        self.reset_metrics()
        scalar_input = not isinstance(v0, np.ndarray)
        v = v0 if isinstance(v0, np.ndarray) else np.array([v0])

        # Create a wrapper that ensures the derivative_fn works with NDArray
        def _derivative_wrapper(
            arr: NDArray[np.floating[Any]],
        ) -> NDArray[np.floating[Any]]:
            if scalar_input and arr.size == 1:
                result = derivative_fn(float(arr[0]))
            else:
                result = derivative_fn(arr)
            if isinstance(result, np.ndarray):
                return result
            return np.array([result])

        for step in range(steps):
            if self.config.integration_scheme == IntegrationScheme.EULER:
                v = self._euler_step(v, _derivative_wrapper)
            else:  # RK4
                v = self._rk4_step(v, _derivative_wrapper)

            # Clamping
            if clamp:
                v_clamped = np.clip(v, self.config.potential_min_v, self.config.potential_max_v)
                clamped = np.sum(v != v_clamped)
                self._metrics.clamping_events += int(clamped)
                v = v_clamped

            # Stability check
            if self.config.check_stability:
                nan_count = int(np.sum(np.isnan(v)))
                inf_count = int(np.sum(np.isinf(v)))

                if nan_count > 0:
                    self._metrics.nan_detected = True
                    raise NumericalInstabilityError(
                        "NaN detected during ODE integration",
                        step=step,
                        field_name="potential",
                        nan_count=nan_count,
                    )
                if inf_count > 0:
                    self._metrics.inf_detected = True
                    raise NumericalInstabilityError(
                        "Inf detected during ODE integration",
                        step=step,
                        field_name="potential",
                        inf_count=inf_count,
                    )

            self._metrics.steps_computed += 1

        # Final metrics
        self._metrics.potential_min_v = float(np.min(v))
        self._metrics.potential_max_v = float(np.max(v))
        self._metrics.potential_mean_v = float(np.mean(v))
        self._metrics.potential_std_v = float(np.std(v))

        result = v if isinstance(v0, np.ndarray) else float(v[0])
        return result, self._metrics

    def _euler_step(
        self,
        v: NDArray[np.floating[Any]],
        derivative_fn: Callable[[NDArray[np.floating[Any]]], NDArray[np.floating[Any]]],
    ) -> NDArray[np.floating[Any]]:
        """
        Perform one explicit Euler integration step.

        V_n+1 = V_n + dt * dV/dt

        Reference: Standard numerical methods (explicit Euler)
        Stability: Requires dt * |dV/dt| < 1 for stability
        """
        dv_dt = derivative_fn(v)
        return cast("NDArray[np.floating[Any]]", v + self.config.dt * dv_dt)

    def _rk4_step(
        self,
        v: NDArray[np.floating[Any]],
        derivative_fn: Callable[[NDArray[np.floating[Any]]], NDArray[np.floating[Any]]],
    ) -> NDArray[np.floating[Any]]:
        """
        Perform one 4th-order Runge-Kutta integration step.

        RK4 provides 4th-order accuracy with better stability than Euler.

        Reference: Standard numerical methods (classical RK4)
        """
        dt = self.config.dt

        k1 = derivative_fn(v)
        k2 = derivative_fn(v + 0.5 * dt * k1)
        k3 = derivative_fn(v + 0.5 * dt * k2)
        k4 = derivative_fn(v + dt * k3)

        return cast("NDArray[np.floating[Any]]", v + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4))

    def validate_potential_range(
        self,
        potential_v: float | NDArray[np.floating],
        strict_physiological: bool = False,
    ) -> bool:
        """
        Validate that potential(s) are within allowed range.

        Parameters
        ----------
        potential_v : float | NDArray
            Potential value(s) in Volts.
        strict_physiological : bool
            If True, use stricter physiological bounds [-95, +40] mV.
            If False, use wider physical bounds [-150, +150] mV.

        Returns
        -------
        bool
            True if all values are within range.
        """
        if strict_physiological:
            v_min, v_max = PHYSIOLOGICAL_V_MIN, PHYSIOLOGICAL_V_MAX
        else:
            v_min, v_max = self.config.potential_min_v, self.config.potential_max_v

        if isinstance(potential_v, np.ndarray):
            return bool(np.all((potential_v >= v_min) & (potential_v <= v_max)))
        else:
            return v_min <= potential_v <= v_max
