"""SelfReadingLoop — orchestrator of five self-reading layers.

Runs parallel to simulation. Read-only access to MFN except
Recovery through the narrow write channel.

Ref: Vasylenko (2026) NFI Platform
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.thermodynamics import ThermodynamicStabilityReport

    from .coherence_monitor import CoherenceReport
    from .interpretability import InterpretabilityTrace
    from .phase_validator import PhaseReport
    from .recovery import RecoveryAction
    from .self_model import SelfModelSnapshot

__all__ = ["SelfReadingConfig", "SelfReadingLoop", "SelfReadingReport"]


@dataclass
class SelfReadingConfig:
    self_model_every: int = 1
    coherence_every: int = 10
    interpretability_window: int = 50
    phase_check_every: int = 100
    recovery_cooldown: int = 200
    pruning_threshold: float = 0.15


@dataclass
class SelfReadingReport:
    """Complete report from one self-reading cycle."""

    step: int
    self_model: SelfModelSnapshot
    coherence: CoherenceReport | None = None
    interpretation: InterpretabilityTrace | None = None
    phase: PhaseReport | None = None
    recovery_action: RecoveryAction | None = None

    def is_healthy(self) -> bool:
        from .phase_validator import MFNPhase

        return self.phase is None or self.phase.phase == MFNPhase.OPERATIONAL

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "step": self.step,
            "active_nodes": self.self_model.active_node_count,
            "entropy": self.self_model.entropy_current,
            "complexity_gradient": self.self_model.complexity_gradient,
            "healthy": self.is_healthy(),
        }
        if self.coherence is not None:
            result["coherence_overall"] = self.coherence.overall
            result["fragmented"] = self.coherence.is_fragmented
        if self.phase is not None:
            result["phase"] = self.phase.phase.value
            result["transition_risk"] = self.phase.transition_risk
        if self.recovery_action is not None:
            result["recovery_mode"] = self.recovery_action.mode.value
            result["recovery_rationale"] = self.recovery_action.rationale
        return result


class SelfReadingLoop:
    """Orchestrator of five self-reading layers.

    Execution order per step:
    1. Always:            SelfModel.capture()
    2. step % N == 0:     CoherenceMonitor.measure()
    3. len >= window:     InterpretabilityLayer.trace()
    4. step % 100 == 0:   PhaseValidator.validate()
    5. phase != OPERATIONAL: Recovery.should_act() -> act()
    """

    def __init__(self, config: SelfReadingConfig | None = None) -> None:
        from .coherence_monitor import CoherenceMonitor
        from .interpretability import InterpretabilityLayer
        from .phase_validator import PhaseValidator
        from .recovery import RecoveryProtocol
        from .self_model import SelfModel

        self.config = config or SelfReadingConfig()
        self.self_model = SelfModel()
        self.coherence = CoherenceMonitor()
        self.interpret = InterpretabilityLayer()
        self.phase_validator = PhaseValidator()
        self.recovery = RecoveryProtocol(
            cooldown=self.config.recovery_cooldown,
            pruning_threshold=self.config.pruning_threshold,
        )

        self._sequences: deque[FieldSequence] = deque(maxlen=500)
        self._self_models: deque[SelfModelSnapshot] = deque(maxlen=500)
        self._phase_reports: deque[PhaseReport] = deque(maxlen=100)
        self._last_coherence: CoherenceReport | None = None
        self._last_phase: PhaseReport | None = None
        self._step: int = 0

    def on_step(
        self,
        seq: FieldSequence,
        thermo_report: ThermodynamicStabilityReport | None = None,
    ) -> SelfReadingReport:
        """Process one simulation step through all layers."""
        step = self._step
        self._step += 1
        self._sequences.append(seq)

        # Layer 1: SelfModel (always)
        sm = self.self_model.capture(seq, step=step)
        self._self_models.append(sm)

        # Layer 2: Coherence (every N steps)
        coh = None
        if step % self.config.coherence_every == 0 and len(self._sequences) >= 2:
            coh = self.coherence.measure(list(self._sequences))
            self._last_coherence = coh

        # Layer 3: Interpretability (when enough data)
        interp = None
        if len(self._sequences) >= self.config.interpretability_window:
            interp = self.interpret.trace(
                list(self._sequences),
                window=self.config.interpretability_window,
            )

        # Layer 4: Phase (every 100 steps)
        phase = None
        if step % self.config.phase_check_every == 0:
            phase = self.phase_validator.validate(seq, thermo_report)
            self._phase_reports.append(phase)
            self._last_phase = phase

        # Layer 5: Recovery (if phase != OPERATIONAL)
        recovery = None
        if self._last_phase is not None and self._last_coherence is not None:
            from .phase_validator import MFNPhase

            if self._last_phase.phase != MFNPhase.OPERATIONAL:
                recovery = self.recovery.act(
                    self._last_phase, self._last_coherence, step,
                )

        return SelfReadingReport(
            step=step,
            self_model=sm,
            coherence=coh,
            interpretation=interp,
            phase=phase,
            recovery_action=recovery,
        )

    def reset(self) -> None:
        """Reset all layers."""
        self._sequences.clear()
        self._self_models.clear()
        self._phase_reports.clear()
        self.self_model.reset()
        self.phase_validator.reset()
        self._last_coherence = None
        self._last_phase = None
        self._step = 0
