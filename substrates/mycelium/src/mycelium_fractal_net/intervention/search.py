"""Search Space Builder — generates candidate interventions.

Builds a constrained search space from allowed levers, bounds, and budget.
Generates deterministic candidate sets via grid search.
"""

from __future__ import annotations

import itertools

import numpy as np

from .levers import get_lever
from .types import InterventionSpec, PlausibilityTag


def build_candidates(
    allowed_levers: list[str],
    current_values: dict[str, float],
    budget: float,
    max_candidates: int = 64,
    seed: int | None = None,
) -> list[tuple[InterventionSpec, ...]]:
    """Generate candidate intervention sets within budget.

    Uses grid search over lever bounds with budget filtering.
    Deterministic when seed is provided.
    """
    rng = np.random.default_rng(seed)

    # Build per-lever candidate values
    lever_candidates: dict[str, list[float]] = {}
    for name in allowed_levers:
        lever = get_lever(name)
        current = current_values.get(name, lever.default)
        lo, hi = lever.bounds
        # Generate grid points
        n_points = max(3, int((hi - lo) / lever.step) + 1)
        n_points = min(n_points, 8)  # Cap per-lever grid
        values = np.linspace(lo, hi, n_points).tolist()
        # Always include current value
        if current not in values:
            values.append(current)
            values.sort()
        lever_candidates[name] = values

    # Generate combinations (bounded)
    all_combos: list[tuple[InterventionSpec, ...]] = []
    lever_names = sorted(lever_candidates.keys())

    if len(lever_names) <= 3:
        # Full grid for small lever sets
        value_lists = [lever_candidates[n] for n in lever_names]
        for combo in itertools.product(*value_lists):
            specs = []
            total_cost = 0.0
            for name, value in zip(lever_names, combo, strict=False):
                lever = get_lever(name)
                current = current_values.get(name, lever.default)
                cost = lever.cost(value)
                total_cost += cost
                specs.append(
                    InterventionSpec(
                        name=name,
                        current_value=current,
                        proposed_value=value,
                        bounds=lever.bounds,
                        step=lever.step,
                        cost=cost,
                        plausibility_tag=PlausibilityTag(lever.plausibility),
                    )
                )
            if total_cost <= budget:
                all_combos.append(tuple(specs))
    else:
        # Random sampling for larger spaces
        for _ in range(max_candidates * 4):
            specs = []
            total_cost = 0.0
            for name in lever_names:
                lever = get_lever(name)
                current = current_values.get(name, lever.default)
                values = lever_candidates[name]
                value = float(rng.choice(values))
                cost = lever.cost(value)
                total_cost += cost
                specs.append(
                    InterventionSpec(
                        name=name,
                        current_value=current,
                        proposed_value=value,
                        bounds=lever.bounds,
                        step=lever.step,
                        cost=cost,
                        plausibility_tag=PlausibilityTag(lever.plausibility),
                    )
                )
            if total_cost <= budget:
                all_combos.append(tuple(specs))

    # Deduplicate and limit
    seen: set[tuple[float, ...]] = set()
    unique: list[tuple[InterventionSpec, ...]] = []
    for candidate_combo in all_combos:
        key = tuple(s.proposed_value for s in candidate_combo)
        if key not in seen:
            seen.add(key)
            unique.append(candidate_combo)
    unique.sort(key=lambda c: sum(s.cost for s in c))
    return unique[:max_candidates]
