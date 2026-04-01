from __future__ import annotations

"""Thin compatibility layer for legacy numerical update-rule entrypoints.

Canonical simulation ownership lives in :mod:`mycelium_fractal_net.core.reaction_diffusion_engine`.
This module preserves the legacy numerics surface while delegating every state update to the
canonical kernel helpers. No independent equation-of-motion logic may live here.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from mycelium_fractal_net.core.reaction_diffusion_engine import (
    DEFAULT_D_ACTIVATOR,
    DEFAULT_D_INHIBITOR,
    DEFAULT_R_ACTIVATOR,
    DEFAULT_R_INHIBITOR,
    DEFAULT_TURING_THRESHOLD,
    ReactionDiffusionConfig,
    compat_activator_inhibitor_step,
    compat_apply_growth_event,
    compat_apply_quantum_jitter,
    compat_apply_turing_to_field,
    compat_clamp_field,
    compat_diffusion_step,
    compat_full_step,
    compat_validate_cfl_condition,
)
from mycelium_fractal_net.core.reaction_diffusion_engine import (
    DEFAULT_FIELD_ALPHA as DEFAULT_ALPHA,
)
from mycelium_fractal_net.core.reaction_diffusion_engine import (
    BoundaryCondition as CoreBoundaryCondition,
)
from mycelium_fractal_net.numerics.grid_ops import BoundaryCondition

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _to_core_boundary(
    boundary: BoundaryCondition | CoreBoundaryCondition,
) -> CoreBoundaryCondition:
    if isinstance(boundary, CoreBoundaryCondition):
        return boundary
    return CoreBoundaryCondition(boundary.value)


@dataclass
class UpdateParameters:
    d_activator: float = DEFAULT_D_ACTIVATOR
    d_inhibitor: float = DEFAULT_D_INHIBITOR
    r_activator: float = DEFAULT_R_ACTIVATOR
    r_inhibitor: float = DEFAULT_R_INHIBITOR
    alpha: float = DEFAULT_ALPHA
    turing_threshold: float = DEFAULT_TURING_THRESHOLD
    turing_contribution_v: float = 0.005
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC


def diffusion_update(
    field: NDArray[np.floating[Any]],
    diffusion_coeff: float,
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC,
    check_stability: bool = True,
) -> NDArray[np.floating[Any]]:
    return compat_diffusion_step(
        np.asarray(field, dtype=np.float64),
        float(diffusion_coeff),
        _to_core_boundary(boundary),
        check_stability=check_stability,
    )


def activator_inhibitor_update(
    activator: NDArray[np.floating[Any]],
    inhibitor: NDArray[np.floating[Any]],
    params: UpdateParameters | None = None,
    check_stability: bool = True,
) -> tuple[NDArray[np.floating[Any]], NDArray[np.floating[Any]]]:
    params = params or UpdateParameters()
    config = ReactionDiffusionConfig(
        grid_size=int(np.asarray(activator).shape[0]),
        d_activator=float(params.d_activator),
        d_inhibitor=float(params.d_inhibitor),
        r_activator=float(params.r_activator),
        r_inhibitor=float(params.r_inhibitor),
        turing_threshold=float(params.turing_threshold),
        alpha=float(params.alpha),
        boundary_condition=_to_core_boundary(params.boundary),
        check_stability=check_stability,
        spike_probability=0.0,
    )
    return compat_activator_inhibitor_step(
        np.asarray(activator, dtype=np.float64),
        np.asarray(inhibitor, dtype=np.float64),
        config,
        check_stability=check_stability,
    )


def apply_turing_to_field(
    field: NDArray[np.floating[Any]],
    activator: NDArray[np.floating[Any]],
    threshold: float = DEFAULT_TURING_THRESHOLD,
    contribution_v: float = 0.005,
) -> tuple[NDArray[np.floating[Any]], int]:
    return compat_apply_turing_to_field(
        np.asarray(field, dtype=np.float64),
        np.asarray(activator, dtype=np.float64),
        threshold=float(threshold),
        contribution_v=float(contribution_v),
    )


def apply_growth_event(
    field: NDArray[np.floating[Any]],
    rng: np.random.Generator,
    spike_probability: float = 0.25,
) -> tuple[NDArray[np.floating[Any]], int]:
    return compat_apply_growth_event(
        np.asarray(field, dtype=np.float64),
        rng,
        spike_probability=float(spike_probability),
    )


def apply_quantum_jitter(
    field: NDArray[np.floating[Any]],
    rng: np.random.Generator,
    jitter_var: float = 0.0005,
) -> NDArray[np.floating[Any]]:
    return compat_apply_quantum_jitter(
        np.asarray(field, dtype=np.float64),
        rng,
        jitter_var=float(jitter_var),
    )


def clamp_potential_field(
    field: NDArray[np.floating[Any]],
) -> tuple[NDArray[np.floating[Any]], int]:
    return compat_clamp_field(np.asarray(field, dtype=np.float64))


def full_simulation_step(
    field: NDArray[np.floating[Any]],
    activator: NDArray[np.floating[Any]],
    inhibitor: NDArray[np.floating[Any]],
    rng: np.random.Generator,
    params: UpdateParameters | None = None,
    *,
    turing_enabled: bool = True,
    quantum_jitter: bool = False,
    check_stability: bool = True,
) -> tuple[
    NDArray[np.floating[Any]],
    NDArray[np.floating[Any]],
    NDArray[np.floating[Any]],
    dict[str, int],
]:
    params = params or UpdateParameters()
    config = ReactionDiffusionConfig(
        grid_size=int(np.asarray(field).shape[0]),
        d_activator=float(params.d_activator),
        d_inhibitor=float(params.d_inhibitor),
        r_activator=float(params.r_activator),
        r_inhibitor=float(params.r_inhibitor),
        turing_threshold=float(params.turing_threshold),
        alpha=float(params.alpha),
        boundary_condition=_to_core_boundary(params.boundary),
        check_stability=check_stability,
        quantum_jitter=bool(quantum_jitter),
        spike_probability=0.25,
    )
    return compat_full_step(
        np.asarray(field, dtype=np.float64),
        np.asarray(activator, dtype=np.float64),
        np.asarray(inhibitor, dtype=np.float64),
        rng,
        config,
        turing_enabled=turing_enabled,
    )


def validate_cfl_condition(diffusion_coeff: float) -> bool:
    return compat_validate_cfl_condition(float(diffusion_coeff))
