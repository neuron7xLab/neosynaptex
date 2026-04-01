"""
Turing Morphogenesis Module.

This module provides the public API for Turing reaction-diffusion pattern
formation, re-exporting validated implementations from model.py for
backward compatibility, plus the new ReactionDiffusionEngine for advanced use.

Conceptual domain: Reaction-diffusion dynamics, pattern formation

Reference:
    - docs/MFN_MATH_MODEL.md Section 2 (Reaction-Diffusion Processes)
    - docs/ARCHITECTURE.md Section 2 (Mycelium Field Simulation)

Mathematical Model:
    ∂a/∂t = D_a ∇²a + r_a·a(1-a) - i    (Activator)
    ∂i/∂t = D_i ∇²i + r_i·(a - i)        (Inhibitor)

Parameters:
    D_a = 0.1 grid²/step    - Activator diffusion
    D_i = 0.05 grid²/step   - Inhibitor diffusion
    r_a = 0.01              - Activator reaction rate
    r_i = 0.02              - Inhibitor reaction rate
    θ = 0.75                - Turing activation threshold

Example:
    >>> from mycelium_fractal_net.core.turing import simulate_mycelium_field
    >>> import numpy as np
    >>> rng = np.random.default_rng(42)
    >>> field, growth_events = simulate_mycelium_field(
    ...     rng=rng,
    ...     grid_size=64,
    ...     steps=64,
    ...     turing_enabled=True
    ... )
    >>> # field: [-95, 40] mV range
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

# Re-export validated reaction-diffusion engine for advanced use
from .reaction_diffusion_engine import (
    DEFAULT_D_ACTIVATOR,
    DEFAULT_D_INHIBITOR,
    DEFAULT_FIELD_ALPHA,
    DEFAULT_QUANTUM_JITTER_VAR,
    DEFAULT_R_ACTIVATOR,
    DEFAULT_R_INHIBITOR,
    DEFAULT_TURING_THRESHOLD,
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    ReactionDiffusionMetrics,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Re-exported constants
TURING_THRESHOLD = DEFAULT_TURING_THRESHOLD
D_ACTIVATOR = DEFAULT_D_ACTIVATOR
D_INHIBITOR = DEFAULT_D_INHIBITOR
R_ACTIVATOR = DEFAULT_R_ACTIVATOR
R_INHIBITOR = DEFAULT_R_INHIBITOR
FIELD_ALPHA = DEFAULT_FIELD_ALPHA
QUANTUM_JITTER_VAR = DEFAULT_QUANTUM_JITTER_VAR


def simulate_mycelium_field(
    rng: np.random.Generator,
    grid_size: int = 64,
    steps: int = 64,
    alpha: float = 0.18,
    spike_probability: float = 0.25,
    turing_enabled: bool = True,
    turing_threshold: float = TURING_THRESHOLD,
    quantum_jitter: bool = False,
    jitter_var: float = QUANTUM_JITTER_VAR,
) -> tuple[NDArray[Any], int]:
    """Simulate mycelium-like potential field on 2D lattice with Turing morphogenesis.

    Returns (field, growth_events). Field in volts, clamped to [-95, 40] mV.
    """
    field = rng.normal(loc=-0.07, scale=0.005, size=(grid_size, grid_size))
    growth_events = 0

    if turing_enabled:
        activator = rng.uniform(0, 0.1, size=(grid_size, grid_size))
        inhibitor = rng.uniform(0, 0.1, size=(grid_size, grid_size))
        da, di = 0.1, 0.05
        ra, ri = 0.01, 0.02

    for _step in range(steps):
        if rng.random() < spike_probability:
            i = int(rng.integers(0, grid_size))
            j = int(rng.integers(0, grid_size))
            field[i, j] += float(rng.normal(loc=0.02, scale=0.005))
            growth_events += 1

        up = np.roll(field, 1, axis=0)
        down = np.roll(field, -1, axis=0)
        left = np.roll(field, 1, axis=1)
        right = np.roll(field, -1, axis=1)
        laplacian = up + down + left + right - 4.0 * field
        field = field + alpha * laplacian

        if turing_enabled:
            a_lap = (
                np.roll(activator, 1, axis=0)
                + np.roll(activator, -1, axis=0)
                + np.roll(activator, 1, axis=1)
                + np.roll(activator, -1, axis=1)
                - 4.0 * activator
            )
            i_lap = (
                np.roll(inhibitor, 1, axis=0)
                + np.roll(inhibitor, -1, axis=0)
                + np.roll(inhibitor, 1, axis=1)
                + np.roll(inhibitor, -1, axis=1)
                - 4.0 * inhibitor
            )
            activator += da * a_lap + ra * (activator * (1 - activator) - inhibitor)
            inhibitor += di * i_lap + ri * (activator - inhibitor)
            turing_mask = activator > turing_threshold
            field[turing_mask] += 0.005
            activator = np.clip(activator, 0, 1)
            inhibitor = np.clip(inhibitor, 0, 1)

        if quantum_jitter:
            jitter = rng.normal(0, np.sqrt(jitter_var), size=field.shape)
            field += jitter

        field = np.clip(field, -0.095, 0.040)

    return field, growth_events


__all__ = [
    "D_ACTIVATOR",
    "D_INHIBITOR",
    "FIELD_ALPHA",
    "QUANTUM_JITTER_VAR",
    "R_ACTIVATOR",
    "R_INHIBITOR",
    # Constants
    "TURING_THRESHOLD",
    # Classes
    "ReactionDiffusionConfig",
    "ReactionDiffusionEngine",
    "ReactionDiffusionMetrics",
    # Functions
    "simulate_mycelium_field",
]
