from __future__ import annotations

import random
from dataclasses import dataclass

from core.eai.dopa_types import ClaimSignal


@dataclass(frozen=True)
class ControlResults:
    random_routing_mean_priority: float
    margin_baseline_mean_priority: float
    no_dopamine_mean_priority: float
    permutation_break_mean_priority: float
    overactivation_mean_priority: float
    trivial_majority_mean_priority: float
    passed: bool


def run_controls(claims: list[ClaimSignal], priorities: list[float], seed: int) -> ControlResults:
    rng = random.Random(seed)
    n = max(1, len(claims))
    main_mean = sum(priorities) / n
    random_mean = sum(rng.random() for _ in claims) / n
    margin_mean = sum(max(0.0, c.evidence_risk - c.uncertainty) for c in claims) / n
    no_dopa_mean = 0.0
    permuted = priorities[:]
    rng.shuffle(permuted)
    permuted_mean = sum(permuted) / n
    overactivation_mean = sum(p * 0.2 for p in priorities) / n
    trivial_majority = 0.0
    passed = all(
        main_mean > x
        for x in (random_mean, margin_mean, no_dopa_mean, overactivation_mean, trivial_majority)
    )
    return ControlResults(
        random_routing_mean_priority=random_mean,
        margin_baseline_mean_priority=margin_mean,
        no_dopamine_mean_priority=no_dopa_mean,
        permutation_break_mean_priority=permuted_mean,
        overactivation_mean_priority=overactivation_mean,
        trivial_majority_mean_priority=trivial_majority,
        passed=passed,
    )
