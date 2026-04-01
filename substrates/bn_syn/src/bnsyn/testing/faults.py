"""Fault injection framework for chaos engineering tests.

This module provides context managers and utilities for injecting controlled
faults into the BN-Syn system to test resilience and error handling.

All fault injections are deterministic and seeded for reproducibility.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import numpy as np

from bnsyn.rng import seed_all


@dataclass
class FaultConfig:
    """Configuration for fault injection.

    Parameters
    ----------
    enabled : bool
        Whether fault injection is enabled.
    seed : int
        Random seed for deterministic fault injection.
    probability : float
        Probability of fault occurring (0.0 to 1.0).
    """

    enabled: bool = True
    seed: int = 42
    probability: float = 0.1


class FaultInjector:
    """Base class for fault injection."""

    def __init__(self, config: FaultConfig) -> None:
        """Initialize fault injector.

        Parameters
        ----------
        config : FaultConfig
            Fault injection configuration.
        """
        self.config = config
        # Use bnsyn.rng for deterministic RNG (compliant with A1: Determinism)
        rng_pack = seed_all(config.seed)
        self.np_rng = rng_pack.np_rng

    def should_inject(self) -> bool:
        """Determine if a fault should be injected at this call.

        Returns
        -------
        bool
            True if fault should be injected.
        """
        if not self.config.enabled:
            return False
        return float(self.np_rng.random()) < self.config.probability


@contextmanager
def inject_numeric_fault(
    config: FaultConfig, fault_type: str = "nan"
) -> Iterator[Callable[[np.ndarray], np.ndarray]]:
    """Inject numeric faults (NaN, inf) into numpy arrays.

    Parameters
    ----------
    config : FaultConfig
        Fault configuration.
    fault_type : str
        Type of numeric fault: "nan", "inf", or "neg_inf".

    Yields
    ------
    Callable[[np.ndarray], np.ndarray]
        Function that potentially injects faults into arrays.

    Examples
    --------
    >>> config = FaultConfig(enabled=True, seed=42, probability=1.0)
    >>> with inject_numeric_fault(config, "nan") as inject:
    ...     weights = np.array([1.0, 2.0, 3.0])
    ...     faulty_weights = inject(weights)
    """
    injector = FaultInjector(config)

    def inject_fn(arr: np.ndarray) -> np.ndarray:
        """Inject fault into array if conditions are met."""
        if not injector.should_inject():
            return arr

        arr_copy = arr.copy()
        # Pick a random index to corrupt
        if arr_copy.size > 0:
            idx = int(injector.np_rng.integers(0, arr_copy.size))
            flat = arr_copy.ravel()
            if fault_type == "nan":
                flat[idx] = np.nan
            elif fault_type == "inf":
                flat[idx] = np.inf
            elif fault_type == "neg_inf":
                flat[idx] = -np.inf
        return arr_copy

    yield inject_fn


@contextmanager
def inject_timing_fault(
    config: FaultConfig, jitter_factor: float = 0.1
) -> Iterator[Callable[[float], float]]:
    """Inject timing jitter into dt values.

    Parameters
    ----------
    config : FaultConfig
        Fault configuration.
    jitter_factor : float
        Maximum relative jitter as fraction of dt (default 0.1 = ±10%).

    Yields
    ------
    Callable[[float], float]
        Function that adds jitter to dt values.

    Examples
    --------
    >>> config = FaultConfig(enabled=True, seed=42, probability=1.0)
    >>> with inject_timing_fault(config, jitter_factor=0.1) as inject:
    ...     dt_jittered = inject(0.1)  # Will be 0.1 ± 10%
    """
    injector = FaultInjector(config)

    def inject_fn(dt: float) -> float:
        """Add jitter to dt if conditions are met."""
        if not injector.should_inject():
            return dt

        # Add random jitter within ±jitter_factor
        jitter = float(injector.np_rng.uniform(-jitter_factor, jitter_factor))
        return dt * (1.0 + jitter)

    yield inject_fn


@contextmanager
def inject_stochastic_fault(
    config: FaultConfig,
) -> Iterator[Callable[[Any], int | None]]:
    """Inject forced RNG reseeds to test determinism violations.

    Parameters
    ----------
    config : FaultConfig
        Fault configuration.

    Yields
    ------
    Callable[[Any], int | None]
        Function that forces RNG reseed with a new seed.

    Examples
    --------
    >>> config = FaultConfig(enabled=True, seed=42, probability=1.0)
    >>> with inject_stochastic_fault(config) as reseed:
    ...     # This will force a reseed with a different seed
    ...     reseed(12345)
    """
    injector = FaultInjector(config)

    def reseed_fn(rng_state: Any) -> int | None:
        """Force RNG reseed if conditions are met.

        Returns
        -------
        int | None
            New seed if reseeding occurred, None otherwise.
        """
        if not injector.should_inject():
            return None

        # Generate a different seed
        new_seed = int(injector.np_rng.integers(0, 2**32 - 1))
        return new_seed

    yield reseed_fn


@contextmanager
def inject_io_fault(
    config: FaultConfig, fault_mode: str = "silent_fail"
) -> Iterator[Callable[[str], bool]]:
    """Inject I/O faults for testing graceful degradation.

    Parameters
    ----------
    config : FaultConfig
        Fault configuration.
    fault_mode : str
        Fault mode: "silent_fail", "corrupt", or "exception".

    Yields
    ------
    Callable[[str], bool]
        Function that simulates I/O failures.

    Examples
    --------
    >>> config = FaultConfig(enabled=True, seed=42, probability=1.0)
    >>> with inject_io_fault(config, "silent_fail") as fail:
    ...     success = fail("output.json")  # Will return False
    """
    injector = FaultInjector(config)

    def fail_fn(path: str) -> bool:
        """Simulate I/O failure if conditions are met.

        Returns
        -------
        bool
            False if I/O should fail, True if should succeed.
        """
        if not injector.should_inject():
            return True  # Success - no fault

        if fault_mode == "exception":
            raise IOError(f"Simulated I/O fault for: {path}")
        elif fault_mode == "corrupt":
            # Indicate that corruption occurred
            return False
        else:  # silent_fail
            return False

    yield fail_fn


def validate_numeric_health(arr: np.ndarray, name: str = "array") -> None:
    """Validate that array contains no NaN or inf values.

    Parameters
    ----------
    arr : np.ndarray
        Array to validate.
    name : str
        Name for error messages.

    Raises
    ------
    ValueError
        If array contains NaN or inf values.
    """
    if np.any(np.isnan(arr)):
        raise ValueError(f"{name} contains NaN values")
    if np.any(np.isinf(arr)):
        raise ValueError(f"{name} contains inf values")


def clamp_numeric(arr: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """Clamp array values to valid range, replacing invalid values.

    Parameters
    ----------
    arr : np.ndarray
        Array to clamp.
    min_val : float
        Minimum valid value.
    max_val : float
        Maximum valid value.

    Returns
    -------
    np.ndarray
        Clamped array with NaN/inf replaced by bounds.
    """
    result = arr.copy()
    # Replace NaN and inf with clamped values
    result[np.isnan(result)] = min_val
    result[np.isinf(result) & (result > 0)] = max_val
    result[np.isinf(result) & (result < 0)] = min_val
    # Clamp to bounds
    clipped: np.ndarray = np.clip(result, min_val, max_val)
    return clipped
