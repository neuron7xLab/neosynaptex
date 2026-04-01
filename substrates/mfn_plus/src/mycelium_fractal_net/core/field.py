"""
MyceliumField class for 2D potential field simulation.

Provides the main interface for creating and managing mycelium-like fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from .types import SimulationConfig


class MyceliumField:
    """
    2D potential field with mycelium-like dynamics.

    This class encapsulates the state and configuration for simulating
    bio-inspired 2D potential fields with reaction-diffusion dynamics,
    Turing morphogenesis, and optional quantum jitter.

    Attributes
    ----------
    config : SimulationConfig
        Simulation configuration parameters.
    rng : np.random.Generator
        Random number generator for reproducibility.
    field : NDArray[np.float64]
        Current 2D potential field in Volts. Shape (N, N).
    step_count : int
        Number of simulation steps executed.

    Examples
    --------
    >>> from mycelium_fractal_net import SimulationConfig, MyceliumField
    >>> config = SimulationConfig(grid_size=32, steps=10, seed=42)
    >>> mf = MyceliumField(config)
    >>> mf.grid_size
    32
    """

    def __init__(self, config: SimulationConfig) -> None:
        """
        Initialize a MyceliumField.

        Parameters
        ----------
        config : SimulationConfig
            Configuration parameters for the simulation.
        """
        from .types import SimulationConfig as SC

        if not isinstance(config, SC):
            raise TypeError(f"config must be SimulationConfig, got {type(config).__name__}")

        self._config = config
        self._rng = np.random.default_rng(config.seed)
        self._step_count = 0

        # Initialize field with resting potential (~ -70 mV)
        self._field: NDArray[np.float64] = np.full(
            (config.grid_size, config.grid_size),
            -0.070,  # -70 mV in Volts
            dtype=np.float64,
        )

    @property
    def config(self) -> SimulationConfig:
        """Return the simulation configuration."""

        return self._config

    @property
    def rng(self) -> np.random.Generator:
        """Return the random number generator."""
        return self._rng

    @property
    def field(self) -> NDArray[np.float64]:
        """Return the current potential field."""
        return self._field

    @property
    def grid_size(self) -> int:
        """Return the grid size N."""
        return self._config.grid_size

    @property
    def step_count(self) -> int:
        """Return the number of steps executed."""
        return self._step_count

    def reset(self, seed: int | None = None) -> None:
        """
        Reset the field to initial state.

        Parameters
        ----------
        seed : int | None
            New random seed. None keeps current seed behavior.
        """
        if seed is not None:
            # Update configuration seed so downstream consumers see the new value
            # and reinitialize RNG for deterministic resets.
            self._config.seed = seed
            self._rng = np.random.default_rng(seed)
        elif self._config.seed is not None:
            # Recreate RNG from the existing configuration seed to return to the
            # initial deterministic state rather than continuing from the
            # previous generator's advanced state.
            self._rng = np.random.default_rng(self._config.seed)
        else:
            # No seed configured; start with a fresh generator to avoid sharing
            # the advanced state across resets.
            self._rng = np.random.default_rng()
        self._step_count = 0
        self._field = np.full(
            (self._config.grid_size, self._config.grid_size),
            -0.070,
            dtype=np.float64,
        )

    def get_state(self) -> NDArray[np.float64]:
        """
        Return a copy of the current field state.

        Returns
        -------
        NDArray[np.float64]
            Copy of the 2D potential field.
        """
        result: NDArray[np.float64] = self._field.copy()
        return result
