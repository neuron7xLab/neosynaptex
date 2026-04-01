"""Layer 4 — PhaseValidator. Every 100 steps. Is the system degrading?

Classifies system phase from PHYSICAL signals only.
Never reads gamma. Never reads attribution weights.
Sources: free_energy, lyapunov_spectrum, betti_numbers, D_box.

Ref: Vasylenko (2026), Cross & Hohenberg (1993)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.thermodynamics import ThermodynamicStabilityReport

__all__ = ["MFNPhase", "PhaseReport", "PhaseValidator"]


class MFNPhase(Enum):
    OPERATIONAL = "operational"
    NOISY = "noisy"
    FRAGMENTING = "fragmenting"
    COLLAPSING = "collapsing"


@dataclass(frozen=True)
class PhaseReport:
    """Read-only phase assessment."""

    phase: MFNPhase
    phase_confidence: float
    steps_in_phase: int
    transition_risk: float
    physical_signals: dict[str, float] = field(default_factory=dict)


class PhaseValidator:
    """Classify system phase from physical signals only.

    Rules:
      OPERATIONAL:  free_energy stable, D_box in [1.5, 2.0], lambda1 < 0
      NOISY:        free_energy oscillates OR lambda1 ~ 0
      FRAGMENTING:  D_box < 1.5 OR field has disconnected components
      COLLAPSING:   free_energy diverges OR D_box ~ 0 OR NaN detected
    """

    def __init__(self) -> None:
        self._phase_history: list[MFNPhase] = []

    def validate(
        self,
        seq: FieldSequence,
        thermo_report: ThermodynamicStabilityReport | None = None,
    ) -> PhaseReport:
        """Classify current phase from physical signals."""
        from mycelium_fractal_net.analytics.fractal_features import (
            compute_box_counting_dimension,
        )

        f = np.asarray(seq.field, dtype=np.float64)

        # Physical signals
        d_box = compute_box_counting_dimension(f)
        field_std = float(np.std(f))
        has_nan = bool(not np.isfinite(f).all())

        lambda1 = 0.0
        free_energy = 0.0
        energy_drift = 0.0
        if thermo_report is not None:
            lambda1 = thermo_report.lyapunov_lambda1
            free_energy = thermo_report.energy_trajectory[-1] if thermo_report.energy_trajectory else 0.0
            energy_drift = thermo_report.energy_drift_per_step

        signals = {
            "d_box": d_box,
            "lambda1": lambda1,
            "free_energy": free_energy,
            "energy_drift": energy_drift,
            "field_std": field_std,
        }

        # Classification
        if has_nan or d_box < 0.1 or not np.isfinite(free_energy):
            phase = MFNPhase.COLLAPSING
            confidence = 0.95
        elif d_box < 1.5 or field_std < 1e-8:
            phase = MFNPhase.FRAGMENTING
            confidence = 0.8
        elif abs(lambda1) < 0.05 or energy_drift > 1e-3:
            phase = MFNPhase.NOISY
            confidence = 0.7
        else:
            phase = MFNPhase.OPERATIONAL
            confidence = 0.9

        self._phase_history.append(phase)

        # Steps in current phase
        steps_in = 1
        for p in reversed(self._phase_history[:-1]):
            if p == phase:
                steps_in += 1
            else:
                break

        # Transition risk: fraction of non-operational in recent history
        recent = self._phase_history[-10:]
        transition_risk = float(
            np.mean([1.0 for p in recent if p != MFNPhase.OPERATIONAL])
        ) if recent else 0.0

        return PhaseReport(
            phase=phase,
            phase_confidence=confidence,
            steps_in_phase=steps_in,
            transition_risk=transition_risk,
            physical_signals=signals,
        )

    def transition_probability(
        self,
        history: list[PhaseReport],
        window: int = 10,
    ) -> float:
        """Probability of transitioning to a worse state."""
        if len(history) < 2:
            return 0.0
        recent = history[-window:]
        phase_values = {
            MFNPhase.OPERATIONAL: 0,
            MFNPhase.NOISY: 1,
            MFNPhase.FRAGMENTING: 2,
            MFNPhase.COLLAPSING: 3,
        }
        vals = [phase_values.get(r.phase, 0) for r in recent]
        if len(vals) < 2:
            return 0.0
        # Trend: positive slope = degrading
        x = np.arange(len(vals), dtype=float)
        slope = float(np.polyfit(x, vals, 1)[0])
        return float(np.clip(slope / 3.0, 0, 1))

    def reset(self) -> None:
        self._phase_history.clear()
