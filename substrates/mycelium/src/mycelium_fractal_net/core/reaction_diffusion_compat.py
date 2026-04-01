"""Compatibility functions for legacy numerics surface.

These thin wrappers delegate to ReactionDiffusionEngine for backward
compatibility. No independent equation-of-motion logic lives here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from .exceptions import NumericalInstabilityError
from .reaction_diffusion_config import (
    FIELD_V_MAX,
    FIELD_V_MIN,
    MAX_STABLE_DIFFUSION,
    BoundaryCondition,
    ReactionDiffusionConfig,
    _validate_diffusion_coefficient,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray


def compat_validate_cfl_condition(diffusion_coeff: float) -> bool:
    return float(diffusion_coeff) <= MAX_STABLE_DIFFUSION


def _compat_check_array(name: str, arr: NDArray[np.floating[Any]]) -> None:
    nan_count = int(np.sum(np.isnan(arr)))
    inf_count = int(np.sum(np.isinf(arr)))
    if nan_count > 0:
        raise NumericalInstabilityError(
            f"NaN values detected in {name}", field_name=name, nan_count=nan_count
        )
    if inf_count > 0:
        raise NumericalInstabilityError(
            f"Inf values detected in {name}", field_name=name, inf_count=inf_count
        )


def compat_diffusion_step(
    field: NDArray[np.floating[Any]],
    diffusion_coeff: float,
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC,
    *,
    check_stability: bool = True,
) -> NDArray[np.floating[Any]]:
    from .reaction_diffusion_engine import ReactionDiffusionEngine

    _validate_diffusion_coefficient("diffusion_coeff", float(diffusion_coeff), 0.0)
    config = ReactionDiffusionConfig(
        grid_size=int(field.shape[0]),
        alpha=float(diffusion_coeff),
        boundary_condition=boundary,
        check_stability=check_stability,
        spike_probability=0.0,
    )
    engine = ReactionDiffusionEngine(config)
    arr = np.asarray(field, dtype=np.float64)
    updated = arr + float(diffusion_coeff) * engine._compute_laplacian(arr)
    if check_stability:
        _compat_check_array("diffusion_update", updated)
    return np.asarray(updated, dtype=np.float64)


def compat_activator_inhibitor_step(
    activator: NDArray[np.floating[Any]],
    inhibitor: NDArray[np.floating[Any]],
    config: ReactionDiffusionConfig,
    *,
    check_stability: bool = True,
) -> tuple[NDArray[np.floating[Any]], NDArray[np.floating[Any]]]:
    from .reaction_diffusion_engine import ReactionDiffusionEngine

    engine = ReactionDiffusionEngine(config)
    a = np.asarray(activator, dtype=np.float64)
    i = np.asarray(inhibitor, dtype=np.float64)
    a_lap = engine._compute_laplacian(a)
    i_lap = engine._compute_laplacian(i)
    da = config.d_activator * a_lap + config.r_activator * (a * (1 - a) - i)
    di = config.d_inhibitor * i_lap + config.r_inhibitor * (a - i)
    a_new = np.clip(a + da, 0.0, 1.0)
    i_new = np.clip(i + di, 0.0, 1.0)
    if check_stability:
        _compat_check_array("activator", a_new)
        _compat_check_array("inhibitor", i_new)
    return np.asarray(a_new, dtype=np.float64), np.asarray(i_new, dtype=np.float64)


def compat_apply_turing_to_field(
    field: NDArray[np.floating[Any]],
    activator: NDArray[np.floating[Any]],
    *,
    threshold: float,
    contribution_v: float,
) -> tuple[NDArray[np.floating[Any]], int]:
    out = np.asarray(field, dtype=np.float64).copy()
    mask = np.asarray(activator, dtype=np.float64) > float(threshold)
    activation_count = int(np.sum(mask))
    if activation_count:
        out[mask] += float(contribution_v)
    return out, activation_count


def compat_apply_growth_event(
    field: NDArray[np.floating[Any]],
    rng: np.random.Generator,
    *,
    spike_probability: float,
) -> tuple[NDArray[np.floating[Any]], int]:
    out = np.asarray(field, dtype=np.float64).copy()
    growth_mask = rng.random(out.shape) < float(spike_probability)
    event_count = int(np.sum(growth_mask))
    if event_count:
        out[growth_mask] += 0.02
    return out, event_count


def compat_apply_quantum_jitter(
    field: NDArray[np.floating[Any]],
    rng: np.random.Generator,
    *,
    jitter_var: float,
) -> NDArray[np.floating[Any]]:
    out: NDArray[np.floating[Any]] = np.asarray(field, dtype=np.float64).copy()
    if float(jitter_var) <= 0.0:
        return out
    jitter = rng.normal(0.0, np.sqrt(float(jitter_var)), size=out.shape)
    result: NDArray[np.floating[Any]] = np.asarray(out + jitter, dtype=np.float64)
    return result


def compat_clamp_field(
    field: NDArray[np.floating[Any]],
) -> tuple[NDArray[np.floating[Any]], int]:
    out = np.asarray(field, dtype=np.float64).copy()
    clamped_mask = (out > FIELD_V_MAX) | (out < FIELD_V_MIN)
    clamped = int(np.count_nonzero(clamped_mask))
    if clamped:
        np.clip(out, FIELD_V_MIN, FIELD_V_MAX, out=out)
    return out, clamped


def compat_full_step(
    field: NDArray[np.floating[Any]],
    activator: NDArray[np.floating[Any]],
    inhibitor: NDArray[np.floating[Any]],
    rng: np.random.Generator,
    config: ReactionDiffusionConfig,
    *,
    turing_enabled: bool = True,
) -> tuple[
    NDArray[np.floating[Any]],
    NDArray[np.floating[Any]],
    NDArray[np.floating[Any]],
    dict[str, int],
]:
    from .reaction_diffusion_engine import ReactionDiffusionEngine

    engine = ReactionDiffusionEngine(config)
    engine._rng = rng
    engine._field = np.asarray(field, dtype=np.float64).copy()
    engine._activator = np.asarray(activator, dtype=np.float64).copy()
    engine._inhibitor = np.asarray(inhibitor, dtype=np.float64).copy()
    engine._simulation_step(0, turing_enabled=turing_enabled)
    return (
        np.asarray(engine._field, dtype=np.float64),
        np.asarray(engine._activator, dtype=np.float64),
        np.asarray(engine._inhibitor, dtype=np.float64),
        {
            "growth_events": int(engine.metrics.growth_events),
            "turing_activations": int(engine.metrics.turing_activations),
            "clamping_events": int(engine.metrics.clamping_events),
        },
    )
