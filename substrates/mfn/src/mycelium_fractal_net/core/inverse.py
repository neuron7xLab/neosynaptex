"""inverse_synthesis() — find parameters that produce a target diagnostic state.

Coordinate descent over simulation parameters to match a target
transition_type and ews_score.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mycelium_fractal_net.core.early_warning import early_warning
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.inverse import InverseSynthesisResult

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import SimulationSpec

logger = logging.getLogger(__name__)

__all__ = ["inverse_synthesis"]

SEARCH_PARAMS: dict[str, tuple[float, float, float]] = {
    "alpha": (0.05, 0.24, 0.01),
    "spike_probability": (0.0, 1.0, 0.05),
    "gabaa_concentration": (0.0, 80.0, 5.0),
    "serotonergic_plasticity": (0.5, 3.0, 0.2),
}


def _build_spec_from_params(
    params: dict[str, float], grid_size: int, steps: int, seed: int
) -> SimulationSpec:
    from mycelium_fractal_net.types.field import (
        GABAATonicSpec,
        NeuromodulationSpec,
        SerotonergicPlasticitySpec,
        SimulationSpec,
    )

    alpha = params.get("alpha", 0.18)
    spike_prob = params.get("spike_probability", 0.25)
    gabaa_conc = params.get("gabaa_concentration", 0.0)
    sero_plast = params.get("serotonergic_plasticity", 1.0)

    nm = None
    if gabaa_conc > 0.0 or sero_plast != 1.0:
        gabaa = (
            GABAATonicSpec(
                profile="inverse",
                agonist_concentration_um=gabaa_conc,
                shunt_strength=min(gabaa_conc / 100.0, 0.8),
                rest_offset_mv=-(gabaa_conc / 8.0),
                desensitization_rate_hz=0.05,
                recovery_rate_hz=0.02,
            )
            if gabaa_conc > 0.0
            else None
        )
        sero = (
            SerotonergicPlasticitySpec(
                profile="inverse",
                plasticity_scale=sero_plast,
                reorganization_drive=min((sero_plast - 1.0) / 2.0, 0.9),
            )
            if sero_plast != 1.0
            else None
        )
        nm = NeuromodulationSpec(
            profile="inverse", enabled=True, gabaa_tonic=gabaa, serotonergic=sero
        )

    return SimulationSpec(
        grid_size=grid_size,
        steps=steps,
        seed=seed,
        alpha=alpha,
        spike_probability=spike_prob,
        neuromodulation=nm,
    )


def _objective(
    params: dict[str, float],
    target_transition_type: str,
    target_ews_score: float,
    grid_size: int,
    steps: int,
    seed: int,
) -> tuple[float, str, float]:
    """Evaluate how close params are to target. Returns (objective, achieved_type, achieved_score)."""
    try:
        spec = _build_spec_from_params(params, grid_size, steps, seed)
        seq = simulate_history(spec)
        w = early_warning(seq)
        type_match = 1.0 if w.transition_type == target_transition_type else 0.5
        score_dist = abs(w.ews_score - target_ews_score)
        obj = score_dist / type_match
        return obj, w.transition_type, w.ews_score
    except Exception:
        return 999.0, "error", 0.0


def inverse_synthesis(
    target_transition_type: str,
    target_ews_score: float,
    *,
    base_spec: SimulationSpec | None = None,
    grid_size: int = 32,
    steps: int = 60,
    max_iterations: int = 40,
    tolerance: float = 0.05,
    seed: int = 42,
) -> InverseSynthesisResult:
    """Find SimulationSpec parameters that produce a target diagnostic state.

    Uses coordinate descent over alpha, spike_probability, gabaa_concentration,
    and serotonergic_plasticity to minimize distance to target.

    Parameters
    ----------
    target_transition_type : str
        Desired EWS transition type (e.g., "critical_slowing", "flickering").
    target_ews_score : float
        Desired EWS score [0, 1].
    grid_size : int
        Grid size for search simulations.
    steps : int
        Steps per simulation.
    max_iterations : int
        Maximum coordinate descent iterations.
    tolerance : float
        Objective threshold for success.
    seed : int
        Base seed for simulations.

    Returns
    -------
    InverseSynthesisResult
    """
    import numpy as np

    # Initialize from base_spec or defaults
    if base_spec is not None:
        current: dict[str, float] = {
            "alpha": base_spec.alpha,
            "spike_probability": base_spec.spike_probability,
        }
        if base_spec.neuromodulation and base_spec.neuromodulation.gabaa_tonic:
            current["gabaa_concentration"] = (
                base_spec.neuromodulation.gabaa_tonic.agonist_concentration_um
            )
        else:
            current["gabaa_concentration"] = 0.0
        if base_spec.neuromodulation and base_spec.neuromodulation.serotonergic:
            current["serotonergic_plasticity"] = (
                base_spec.neuromodulation.serotonergic.plasticity_scale
            )
        else:
            current["serotonergic_plasticity"] = 1.0
    else:
        current = {
            "alpha": 0.18,
            "spike_probability": 0.25,
            "gabaa_concentration": 0.0,
            "serotonergic_plasticity": 1.0,
        }

    best_obj, best_type, best_score = _objective(
        current, target_transition_type, target_ews_score, grid_size, steps, seed
    )
    best_params = dict(current)
    trajectory: list[dict[str, Any]] = [{"params": dict(current), "objective": best_obj}]

    param_names = list(SEARCH_PARAMS.keys())
    iterations = 0

    for _outer in range(max_iterations):
        improved = False
        for pname in param_names:
            lo, hi, step = SEARCH_PARAMS[pname]
            candidates = np.arange(lo, hi + step / 2, step).tolist()

            for val in candidates:
                trial = dict(current)
                trial[pname] = val
                obj, tt, score = _objective(
                    trial, target_transition_type, target_ews_score, grid_size, steps, seed
                )
                iterations += 1

                if obj < best_obj:
                    best_obj = obj
                    best_type = tt
                    best_score = score
                    best_params = dict(trial)
                    current[pname] = val
                    improved = True

                if best_obj < tolerance:
                    break

            trajectory.append({"params": dict(current), "objective": best_obj})

            if best_obj < tolerance:
                break

        if best_obj < tolerance or not improved:
            break

    synth_spec = _build_spec_from_params(best_params, grid_size, steps, seed)

    return InverseSynthesisResult(
        found=best_obj < tolerance,
        synthesized_spec=synth_spec,
        achieved_transition_type=best_type,
        achieved_ews_score=round(best_score, 4),
        target_transition_type=target_transition_type,
        target_ews_score=target_ews_score,
        objective_value=round(best_obj, 6),
        iterations_used=iterations,
        search_trajectory=tuple(trajectory),
    )
