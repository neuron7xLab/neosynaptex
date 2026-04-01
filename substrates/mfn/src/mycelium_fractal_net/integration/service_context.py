"""
Service context for MyceliumFractalNet.

Provides a unified context object that encapsulates configuration, RNG state,
and handles to numerical engines. This enables consistent behavior across
CLI, API, and experiment entry points.

The ServiceContext implements dependency injection for the numerical core,
allowing clean separation between the integration layer and the mathematical
engines (Nernst, Turing, STDP, Krum).

Reference: docs/ARCHITECTURE.md, docs/MFN_SYSTEM_ROLE.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class ExecutionMode(str, Enum):
    """
    Execution mode for service context.

    Attributes:
        CLI: Command-line interface mode.
        API: HTTP API mode (FastAPI).
        EXPERIMENT: Experiment/research mode.
        LIBRARY: Direct Python library usage.
    """

    CLI = "cli"
    API = "api"
    EXPERIMENT = "experiment"
    LIBRARY = "library"


@dataclass
class ServiceContext:
    """
    Service context encapsulating configuration, RNG, and engine handles.

    Provides a unified interface for all MFN operations, ensuring consistent
    configuration and reproducibility across different execution modes.

    Attributes:
        seed: Random seed for reproducibility. None means non-deterministic.
        mode: Execution mode (CLI, API, experiment, library).
        grid_size: Default grid size for simulations.
        steps: Default number of simulation steps.
        turing_enabled: Default Turing morphogenesis setting.
        quantum_jitter: Default quantum jitter setting.
        _rng: Internal RNG instance (created lazily).
        _metadata: Optional metadata dictionary for logging/tracing.

    Example:
        >>> ctx = ServiceContext(seed=42, mode=ExecutionMode.API)
        >>> rng = ctx.get_rng()
        >>> # Use rng for reproducible operations
    """

    seed: int | None = 42
    mode: ExecutionMode = ExecutionMode.LIBRARY
    grid_size: int = 64
    steps: int = 64
    turing_enabled: bool = True
    quantum_jitter: bool = False
    _rng: np.random.Generator | None = field(default=None, repr=False)
    _metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Initialize RNG if seed is provided."""
        if self._rng is None and self.seed is not None:
            self._rng = np.random.default_rng(self.seed)

    @property
    def rng(self) -> np.random.Generator:
        """
        Get the random number generator for this context.

        Returns:
            np.random.Generator: Seeded or unseeded RNG.

        Note:
            If seed is None, returns a new unseeded generator each time.
            If seed is set, returns the same generator instance for reproducibility.
        """
        if self._rng is None:
            return np.random.default_rng()
        return self._rng

    def get_rng(self) -> np.random.Generator:
        """
        Get the random number generator for this context.

        Returns:
            np.random.Generator: Seeded or unseeded RNG.

        Note:
            If seed is None, returns a new unseeded generator each time.
            If seed is set, returns the same generator instance for reproducibility.

        Deprecated:
            Use the `rng` property instead.
        """
        return self.rng

    def reset_rng(self) -> None:
        """
        Reset the RNG to initial state (re-seed with same seed).

        Useful for running multiple reproducible experiments.
        """
        if self.seed is not None:
            self._rng = np.random.default_rng(self.seed)

    def with_seed(self, seed: int) -> ServiceContext:
        """
        Create a new context with a different seed.

        Args:
            seed: New random seed.

        Returns:
            ServiceContext: New context with the specified seed.
        """
        return ServiceContext(
            seed=seed,
            mode=self.mode,
            grid_size=self.grid_size,
            steps=self.steps,
            turing_enabled=self.turing_enabled,
            quantum_jitter=self.quantum_jitter,
            _metadata=self._metadata.copy(),
        )

    def with_mode(self, mode: ExecutionMode) -> ServiceContext:
        """
        Create a new context with a different execution mode.

        Args:
            mode: New execution mode.

        Returns:
            ServiceContext: New context with the specified mode.
        """
        return ServiceContext(
            seed=self.seed,
            mode=mode,
            grid_size=self.grid_size,
            steps=self.steps,
            turing_enabled=self.turing_enabled,
            quantum_jitter=self.quantum_jitter,
            _rng=self._rng,
            _metadata=self._metadata.copy(),
        )

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set metadata for logging/tracing.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key.
            default: Default value if key not found.

        Returns:
            Metadata value or default.
        """
        return self._metadata.get(key, default)


def create_context_from_request(
    seed: int = 42,
    grid_size: int = 64,
    steps: int = 64,
    turing_enabled: bool = True,
    quantum_jitter: bool = False,
    mode: ExecutionMode = ExecutionMode.API,
) -> ServiceContext:
    """
    Create a service context from request parameters.

    Factory function for creating ServiceContext from API/CLI parameters.

    Args:
        seed: Random seed for reproducibility.
        grid_size: Simulation grid size.
        steps: Number of simulation steps.
        turing_enabled: Enable Turing morphogenesis.
        quantum_jitter: Enable quantum noise.
        mode: Execution mode.

    Returns:
        ServiceContext: Configured service context.

    Example:
        >>> ctx = create_context_from_request(seed=42, mode=ExecutionMode.CLI)
    """
    return ServiceContext(
        seed=seed,
        mode=mode,
        grid_size=grid_size,
        steps=steps,
        turing_enabled=turing_enabled,
        quantum_jitter=quantum_jitter,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ExecutionMode",
    "ServiceContext",
    "create_context_from_request",
]
