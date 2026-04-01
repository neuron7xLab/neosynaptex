"""Layer 2 — CoherenceMonitor. Every N steps. Is the system intact?

Measures connectivity, module conflict, intent gap, stability.
Read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

__all__ = ["CoherenceMonitor", "CoherenceReport"]


@dataclass(frozen=True)
class CoherenceReport:
    """Read-only coherence assessment."""

    connectivity: float  # spectral graph connectivity [0, 1]
    module_conflict: float  # cosine distance between quadrants [0, 1]
    intent_gap: float  # ||target - current|| / ||target|| [0, 1]
    stability_index: float  # std(entropy) in window [0, inf)
    overall: float  # harmonic mean of all metrics

    @property
    def is_fragmented(self) -> bool:
        return self.connectivity < 0.4 or self.module_conflict > 0.6

    @property
    def is_drifting(self) -> bool:
        return self.stability_index > 0.3


class CoherenceMonitor:
    """Measures system coherence from field sequences."""

    def measure(
        self,
        sequences: list[FieldSequence],
        window: int = 10,
    ) -> CoherenceReport:
        """Compute coherence from recent field snapshots."""
        if not sequences:
            return CoherenceReport(0.0, 1.0, 1.0, 1.0, 0.0)

        recent = sequences[-window:]
        fields = [np.asarray(s.field, dtype=np.float64) for s in recent]

        # Connectivity: correlation between adjacent pixels (spatial coherence)
        last = fields[-1]
        rolled = np.roll(last, 1, axis=0)
        corr = float(np.corrcoef(last.ravel(), rolled.ravel())[0, 1])
        connectivity = float(np.clip((corr + 1) / 2, 0, 1))

        # Module conflict: cosine distance between quadrants
        h, w = last.shape
        q1 = last[: h // 2, : w // 2].ravel()
        q2 = last[: h // 2, w // 2 :].ravel()
        q3 = last[h // 2 :, : w // 2].ravel()
        q4 = last[h // 2 :, w // 2 :].ravel()

        def _cos_dist(a: np.ndarray, b: np.ndarray) -> float:
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            if na < 1e-12 or nb < 1e-12:
                return 1.0
            return float(1.0 - np.dot(a, b) / (na * nb))

        conflict = float(np.mean([
            _cos_dist(q1, q2), _cos_dist(q1, q3),
            _cos_dist(q2, q4), _cos_dist(q3, q4),
        ]))

        # Intent gap: deviation of last field from mean of window
        if len(fields) > 1:
            mean_field = np.mean(fields, axis=0)
            norm_mean = float(np.linalg.norm(mean_field))
            if norm_mean > 1e-12:
                intent_gap = float(np.linalg.norm(last - mean_field) / norm_mean)
            else:
                intent_gap = 0.0
        else:
            intent_gap = 0.0
        intent_gap = float(np.clip(intent_gap, 0, 1))

        # Stability: std of field std across window
        stds = [float(np.std(f)) for f in fields]
        stability_index = float(np.std(stds)) if len(stds) > 1 else 0.0

        # Overall: harmonic mean of positive metrics
        vals = [
            max(connectivity, 1e-12),
            max(1.0 - conflict, 1e-12),
            max(1.0 - intent_gap, 1e-12),
            max(1.0 - min(stability_index, 1.0), 1e-12),
        ]
        overall = float(len(vals) / sum(1.0 / v for v in vals))

        return CoherenceReport(
            connectivity=connectivity,
            module_conflict=conflict,
            intent_gap=intent_gap,
            stability_index=stability_index,
            overall=overall,
        )
