"""Layer 1 — SelfModel. Every step. What is the system now?

Read-only snapshot of system complexity and structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

__all__ = ["SelfModel", "SelfModelSnapshot"]


@dataclass(frozen=True)
class SelfModelSnapshot:
    """Read-only. What MFN is at step t."""

    active_node_count: int
    dominant_contour: str
    complexity_gradient: float  # dEntropy/dt
    entropy_current: float
    field_energy: float
    step: int


class SelfModel:
    """Captures per-step self-model from FieldSequence."""

    def __init__(self) -> None:
        self._prev_entropy: float | None = None

    def capture(self, seq: FieldSequence, step: int = 0) -> SelfModelSnapshot:
        """Extract self-model from current field state."""
        field = np.asarray(seq.field, dtype=np.float64)

        # Entropy via histogram
        hist, _ = np.histogram(field.ravel(), bins=64, density=True)
        hist = hist[hist > 0]
        dx = 1.0 / 64
        entropy = float(-np.sum(hist * np.log(hist + 1e-12) * dx))

        # Complexity gradient
        if self._prev_entropy is not None:
            gradient = entropy - self._prev_entropy
        else:
            gradient = 0.0
        self._prev_entropy = entropy

        # Active nodes: above median threshold
        threshold = float(np.median(field))
        active = int(np.sum(field > threshold))

        # Dominant contour: quadrant with highest mean activation
        h, w = field.shape
        quadrants = {
            "top-left": float(np.mean(field[: h // 2, : w // 2])),
            "top-right": float(np.mean(field[: h // 2, w // 2 :])),
            "bottom-left": float(np.mean(field[h // 2 :, : w // 2])),
            "bottom-right": float(np.mean(field[h // 2 :, w // 2 :])),
        }
        dominant = max(quadrants, key=quadrants.get)  # type: ignore[arg-type]

        # Field energy (L2 norm)
        energy = float(np.sum(field**2))

        return SelfModelSnapshot(
            active_node_count=active,
            dominant_contour=dominant,
            complexity_gradient=gradient,
            entropy_current=entropy,
            field_energy=energy,
            step=step,
        )

    def complexity_is_growing(
        self,
        history: list[SelfModelSnapshot],
        window: int = 10,
    ) -> bool:
        """True if complexity_gradient > 0 consistently in window."""
        if len(history) < window:
            return False
        recent = history[-window:]
        return all(s.complexity_gradient > 0 for s in recent)

    def reset(self) -> None:
        self._prev_entropy = None
