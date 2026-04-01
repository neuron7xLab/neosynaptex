"""Robustness Evaluation — perturbation-based stability assessment.

For each candidate, perturb parameters ±noise and verify the result
remains stable. Unstable candidates get penalized.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from .counterfactual import run_counterfactual
from .types import CounterfactualResult, InterventionSpec

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

logger = logging.getLogger(__name__)

# Perturbation levels (fraction of lever step size)
_PERTURBATION_FRACTIONS = (0.1, 0.25, 0.5)
_N_PERTURBATION_SEEDS = 3


def evaluate_robustness(
    source: FieldSequence,
    result: CounterfactualResult,
    n_perturbations: int = 3,
    seed: int = 42,
) -> float:
    """Evaluate robustness of a candidate via parameter perturbation.

    Returns robustness_score in [0, 1]. 1 = perfectly robust.
    """
    if not result.is_valid or result.detection_after is None:
        return 0.0

    base_label = result.detection_after.label
    base_regime = result.detection_after.regime.label if result.detection_after.regime else "none"

    rng = np.random.default_rng(seed)
    stable_count = 0
    total_count = 0

    for frac in _PERTURBATION_FRACTIONS[:n_perturbations]:
        for _pseed in range(min(_N_PERTURBATION_SEEDS, 2)):
            # Perturb each proposed value by ±frac * step
            perturbed_specs = []
            for spec in result.proposed_changes:
                noise = rng.uniform(-frac, frac) * spec.step
                new_val = spec.proposed_value + noise
                new_val = max(spec.bounds[0], min(spec.bounds[1], new_val))
                perturbed_specs.append(
                    InterventionSpec(
                        name=spec.name,
                        current_value=spec.current_value,
                        proposed_value=new_val,
                        bounds=spec.bounds,
                        step=spec.step,
                        cost=spec.cost,
                        plausibility_tag=spec.plausibility_tag,
                    )
                )

            try:
                perturbed = run_counterfactual(
                    source,
                    tuple(perturbed_specs),
                    horizon=4,
                )
                if perturbed.detection_after is not None:
                    p_label = perturbed.detection_after.label
                    p_regime = (
                        perturbed.detection_after.regime.label
                        if perturbed.detection_after.regime
                        else "none"
                    )
                    if p_label == base_label and p_regime == base_regime:
                        stable_count += 1
            except Exception:
                logger.debug("Perturbation failed", exc_info=True)

            total_count += 1

    if total_count == 0:
        return 0.0
    return round(stable_count / total_count, 4)
