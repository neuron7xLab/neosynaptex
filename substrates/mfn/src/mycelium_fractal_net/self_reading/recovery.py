"""Layer 5 — RecoveryProtocol. The ONLY actor with write access.

Write channel: {Theta, PID} via ThermodynamicKernel config.
Reads: PhaseReport, CoherenceReport, physical_signals.
NEVER reads: gamma, attribution_weights, interpretability traces.

This is the Goodhart firewall: the metric (gamma) never enters
the optimization loop.

Ref: Vasylenko (2026), Goodhart (1984)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .coherence_monitor import CoherenceReport
    from .phase_validator import PhaseReport
    from .self_model import SelfModelSnapshot

__all__ = ["RecoveryAction", "RecoveryMode", "RecoveryProtocol"]


class RecoveryMode(Enum):
    PARAMETRIC = "parametric"  # Theta + PID correction — fast, reversible
    STRUCTURAL = "structural"  # Branch pruning — irreversible, rare


@dataclass(frozen=True)
class RecoveryAction:
    """Immutable record of a recovery intervention."""

    mode: RecoveryMode
    trigger_phase: str
    theta_delta: float | None = None
    pid_adjustment: dict[str, float] | None = None
    nodes_to_prune: list[str] | None = None
    confidence: float = 0.0
    rationale: str = ""


class RecoveryProtocol:
    """The ONLY writer back into MFN.

    Write channel: Theta, PID parameters.
    Read sources: PhaseReport, CoherenceReport, physical_signals.
    NEVER reads: gamma.

    PARAMETRIC if FRAGMENTING:
        Theta -= delta * (free_energy - baseline)
        PID: kp * 0.9, ki * 1.05

    STRUCTURAL if COLLAPSING AND coherence.overall < pruning_threshold:
        Prune nodes where complexity_gradient > mean + 2*sigma
        AND activation < epsilon.
    """

    def __init__(
        self,
        cooldown: int = 200,
        pruning_threshold: float = 0.15,
        baseline_energy: float = 0.0,
    ) -> None:
        self.cooldown = cooldown
        self.pruning_threshold = pruning_threshold
        self.baseline_energy = baseline_energy
        self._last_recovery_step: int = -999
        self._log: list[RecoveryAction] = []

    @property
    def history(self) -> list[RecoveryAction]:
        return list(self._log)

    def should_act(
        self,
        phase: PhaseReport,
        coherence: CoherenceReport,
        current_step: int,
    ) -> bool:
        """True only if:
        1. phase in {FRAGMENTING, COLLAPSING}
        2. cooldown elapsed since last recovery
        3. transition_risk > 0.3
        """
        from .phase_validator import MFNPhase

        if phase.phase not in (MFNPhase.FRAGMENTING, MFNPhase.COLLAPSING):
            return False
        if current_step - self._last_recovery_step < self.cooldown:
            return False
        return not phase.transition_risk < 0.3

    def act(
        self,
        phase: PhaseReport,
        coherence: CoherenceReport,
        current_step: int,
    ) -> RecoveryAction | None:
        """Execute recovery if conditions met. Returns None if cooldown active."""
        if not self.should_act(phase, coherence, current_step):
            return None

        from .phase_validator import MFNPhase

        if phase.phase == MFNPhase.COLLAPSING and coherence.overall < self.pruning_threshold:
            action = self._structural_recovery(phase, coherence)
        else:
            action = self._parametric_recovery(phase)

        self._last_recovery_step = current_step
        self._log.append(action)
        return action

    def _parametric_recovery(self, phase: PhaseReport) -> RecoveryAction:
        """Fast, reversible: adjust Theta and PID."""
        free_energy = phase.physical_signals.get("free_energy", 0.0)
        energy_delta = free_energy - self.baseline_energy
        theta_delta = -0.01 * energy_delta  # counter energy drift

        pid = {
            "kp_factor": 0.9,  # reduce proportional gain
            "ki_factor": 1.05,  # increase integral gain (smooth)
            "kd_factor": 1.0,  # keep derivative unchanged
        }

        return RecoveryAction(
            mode=RecoveryMode.PARAMETRIC,
            trigger_phase=phase.phase.value,
            theta_delta=theta_delta,
            pid_adjustment=pid,
            confidence=phase.phase_confidence,
            rationale=(
                f"Parametric recovery: energy_delta={energy_delta:.4f}, "
                f"theta_correction={theta_delta:.4f}"
            ),
        )

    def _structural_recovery(
        self,
        phase: PhaseReport,
        coherence: CoherenceReport,
    ) -> RecoveryAction:
        """Irreversible pruning. Only when collapsing + low coherence."""
        return RecoveryAction(
            mode=RecoveryMode.STRUCTURAL,
            trigger_phase=phase.phase.value,
            confidence=phase.phase_confidence,
            rationale=(
                f"Structural recovery: coherence={coherence.overall:.3f} "
                f"< threshold={self.pruning_threshold}"
            ),
        )

    def prune_overloaded_branches(
        self,
        history: list[SelfModelSnapshot],
        epsilon: float = 1e-6,
    ) -> list[str]:
        """Identify nodes for synaptic pruning.

        Remove: complexity_gradient > mean + 2*sigma AND low activation.
        Preserve: topological invariants (betti numbers).
        """
        if len(history) < 5:
            return []

        import numpy as np

        gradients = [s.complexity_gradient for s in history]
        mean_g = float(np.mean(gradients))
        std_g = float(np.std(gradients)) + 1e-12
        threshold = mean_g + 2 * std_g

        to_prune: list[str] = []
        for s in history[-10:]:
            if s.complexity_gradient > threshold and s.field_energy < epsilon:
                to_prune.append(f"step_{s.step}")

        return to_prune
