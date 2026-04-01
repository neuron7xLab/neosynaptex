from __future__ import annotations

from .contracts import SigmaIndex


class SigmaEngine:
    def compute(
        self,
        *,
        current_failed_required: int,
        total_required: int,
        content_distance_to_prev: float,
        revision_magnitude: float,
        current_delta: float,
        previous_delta: float,
    ) -> SigmaIndex:
        if total_required <= 0:
            raise ValueError("total_required must be positive")

        conflict_density = min(1.0, current_failed_required / total_required)
        dispersion = min(1.0, max(0.0, content_distance_to_prev))
        revision_elasticity = min(1.0, max(0.0, revision_magnitude))
        # higher slope means better convergence (1 best, 0 worst)
        if previous_delta <= 0:
            convergence_slope = 1.0
        else:
            convergence_slope = min(1.0, max(0.0, 1.0 - max(0.0, current_delta - previous_delta)))

        return SigmaIndex(
            conflict_density=conflict_density,
            dispersion=dispersion,
            revision_elasticity=revision_elasticity,
            convergence_slope=convergence_slope,
        )
