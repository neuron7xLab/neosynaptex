"""Identity Engine — main orchestrator for tau-control.

Processes one step:
  1. CollapseTracker.record() -> Phi
  2. TauController.update()   -> tau
  3. Discriminant.classify()  -> PressureKind
  4. Discriminant.mode()      -> SystemMode
  5. Execute mode action (adapt / transform)
  6. Lyapunov.compute()       -> LyapunovState
  7. Return IdentityReport

gamma is NEVER read by this engine.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .adaptation import adapt_norm
from .collapse_tracker import CollapseTracker
from .discriminant import Discriminant, PressureKind, SystemMode
from .lyapunov import LyapunovMonitor, LyapunovState
from .tau_controller import TauController
from .transformation import TransformationProtocol
from .types import MetaRuleSpace, NormSpace, TauState

__all__ = ["IdentityEngine", "IdentityReport"]


@dataclass(frozen=True)
class IdentityReport:
    """Complete report from one identity engine cycle."""

    tau_state: TauState
    lyapunov: LyapunovState
    norm_updated: bool
    meta_updated: bool
    mechanistic_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.tau_state.to_dict(),
            **self.lyapunov.to_dict(),
            "norm_updated": self.norm_updated,
            "meta_updated": self.meta_updated,
        }


class IdentityEngine:
    """Main orchestrator for identity preservation under pressure."""

    def __init__(
        self,
        state_dim: int = 8,
        collapse_decay: float = 0.95,
        collapse_k_max: int = 3,
        tau_base: float = 3.0,
        tau_max: float = 10.0,
        lyapunov_alpha: float = 0.1,
        lyapunov_beta: float = 0.01,
        delta_max: float = 2.0,
    ) -> None:
        self.tracker = CollapseTracker(decay=collapse_decay, k_max=collapse_k_max)
        self.tau_ctrl = TauController(tau_base=tau_base, tau_max=tau_max)
        self.discriminant = Discriminant()
        self.lyapunov = LyapunovMonitor(
            alpha=lyapunov_alpha, beta=lyapunov_beta, delta_max=delta_max,
        )
        self.transform = TransformationProtocol(lyapunov=self.lyapunov)

        # Initialize norm and meta-rule spaces
        d = state_dim
        self._norm = NormSpace(
            centroid=np.zeros(d),
            shape_matrix=np.eye(d),
            confidence=1.0,
        )
        self._norm_origin = NormSpace(
            centroid=np.zeros(d),
            shape_matrix=np.eye(d),
            confidence=1.0,
        )
        self._meta = MetaRuleSpace()
        self._meta_origin = MetaRuleSpace()
        self._step = 0

    @property
    def norm(self) -> NormSpace:
        return self._norm

    @property
    def meta(self) -> MetaRuleSpace:
        return self._meta

    def process(
        self,
        state_vector: np.ndarray,
        free_energy: float,
        phase_is_collapsing: bool,
        coherence: float,
        recovery_succeeded: bool,
    ) -> IdentityReport:
        """Process one step through the full identity preservation pipeline.

        state_vector: condensed system state (e.g. from FieldSequence features)
        free_energy: V_x from ThermodynamicKernel
        phase_is_collapsing: from PhaseValidator
        coherence: from CoherenceMonitor
        recovery_succeeded: from RecoveryProtocol
        """
        step = self._step
        self._step += 1
        norm_updated = False
        meta_updated = False

        # 1. Collapse tracking
        norm_restored = self._norm.contains(state_vector)
        phi = self.tracker.record(phase_is_collapsing, recovery_succeeded, norm_restored)

        # 2. Tau update
        tau = self.tau_ctrl.update(recovery_succeeded)

        # 3. Pressure classification (with trajectory features)
        pressure = self.discriminant.classify(
            phi=phi,
            tau=tau,
            x=state_vector,
            norm=self._norm,
            phase_is_collapsing=phase_is_collapsing,
            coherence=coherence,
            phi_trend=self.tracker.phi_trend(),
            failure_density=self.tracker.failure_density(),
            steps_in_bad_phase=self.tracker.consecutive_failures,
        )

        # 4. Mode determination
        mode = self.discriminant.mode_from_state(
            pressure, state_vector, self._norm, self._norm_origin,
        )

        # 5. Execute mode action
        transform_triggered = False
        transform_accepted = False

        if mode == SystemMode.TRANSFORMATION:
            transform_triggered = True
            new_meta, accepted = self.transform.transform(
                self._meta, phi, free_energy,
                self._norm, self._norm_origin, self._meta_origin,
            )
            if accepted:
                self._meta = new_meta
                meta_updated = True
                transform_accepted = True
                self.tau_ctrl.notify_transformation()

        elif mode == SystemMode.ADAPTATION:
            self._norm = adapt_norm(
                self._norm, state_vector, recovery_succeeded, self._meta,
            )
            norm_updated = True

        elif mode == SystemMode.RECOVERY:
            # Recovery is handled by self_reading/recovery.py
            # We only update norm tracking here
            self._norm = adapt_norm(
                self._norm, state_vector, False, self._meta,
            )
            norm_updated = True

        # 6. Lyapunov computation
        lyap = self.lyapunov.compute(
            free_energy, self._norm, self._norm_origin,
            self._meta, self._meta_origin,
        )

        # 7. Build report
        note = self._build_note(mode, pressure, phi, tau, transform_accepted)

        tau_state = TauState(
            step=step,
            phi=phi,
            tau=tau,
            pressure=pressure.value,
            mode=mode.value,
            v_x=lyap.v_x,
            v_s=lyap.v_s,
            v_c=lyap.v_c,
            v_total=lyap.v_total,
            transform_triggered=transform_triggered,
            transform_accepted=transform_accepted,
            mechanistic_note=note,
        )

        return IdentityReport(
            tau_state=tau_state,
            lyapunov=lyap,
            norm_updated=norm_updated,
            meta_updated=meta_updated,
            mechanistic_note=note,
        )

    def _build_note(
        self,
        mode: SystemMode,
        pressure: PressureKind,
        phi: float,
        tau: float,
        accepted: bool,
    ) -> str:
        if mode == SystemMode.IDLE:
            return "System nominal. Identity preserved."
        if mode == SystemMode.RECOVERY:
            return f"Recovery mode. Phi={phi:.3f} < tau={tau:.3f}. Projecting state back into norm."
        if mode == SystemMode.ADAPTATION:
            return "Adaptation mode. Norm space updating from experience."
        if mode == SystemMode.TRANSFORMATION:
            if accepted:
                return f"TRANSFORMATION ACCEPTED. Phi={phi:.3f} >= tau={tau:.3f}. Meta-rules updated."
            return f"TRANSFORMATION REJECTED. Bounded jump violated. Phi={phi:.3f}."
        return "Unknown mode."

    def reset(self) -> None:
        self.tracker.reset()
        self.tau_ctrl.reset()
        self.lyapunov.reset()
        self._step = 0
