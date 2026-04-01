"""
DNCA Orchestrator — the full distributed neuromodulatory cognitive architecture.

Wires SPS + 6 NMOs + CompetitionField + MetastabilityEngine + RegimeManager
into a single step() that enforces all 8 invariants.

Cognition = the sequence of winning cycles over time.
Agency = emergent property of competitive dynamics.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

from neuron7x_agents.dnca.competition.kuramoto import KuramotoCoupling
from neuron7x_agents.dnca.competition.lotka_volterra import LotkaVolterraField
from neuron7x_agents.dnca.competition.metastability import MetastabilityEngine
from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.sps import SharedPredictiveState
from neuron7x_agents.dnca.core.types import (
    ACTIVITY_THRESHOLD,
    DNCAAudit,
    FORWARD_MODEL_INNER_STEPS,
    FORWARD_MODEL_LR,
    NMOType,
    PLASTICITY_GATE_THRESHOLD,
    RegimeTransitionEvent,
)
from neuron7x_agents.dnca.neuromodulators import (
    AcetylcholineOperator,
    DopamineOperator,
    GABAOperator,
    GlutamateOperator,
    NorepinephrineOperator,
    SerotoninOperator,
)
from neuron7x_agents.dnca.regime import RegimeManager


@dataclass(slots=True)
class DNCStepOutput:
    """Complete output of one DNCA cycle."""
    dominant_nmo: Optional[str]
    dominant_activity: float
    all_activities: Dict[str, float]
    regime_phase: str
    regime_age: int
    r_order: float
    r_std: float
    mismatch: float
    satiation: float
    plasticity_gate: float
    theta_phase: float
    transition_event: Optional[RegimeTransitionEvent]
    step: int


class DNCA(nn.Module):
    """
    Distributed Neuromodulatory Cognitive Architecture.

    Six operators compete through Lotka-Volterra winnerless competition,
    coupled via Kuramoto phase dynamics, regulated by MetastabilityEngine.
    Each runs its own Dominant-Acceptor cycle over shared predictive state.

    INVARIANTS ENFORCED:
    INV-1: SPS is the only shared resource — NMOs write only designated fields
    INV-2: Dominant forms BEFORE acceptor predicts (DAC runs before modulations write)
    INV-3: Prediction error evaluated against motivational criteria (in DAC)
    INV-4: No NMO permanently wins (Lotka-Volterra + MetastabilityEngine)
    INV-5: Metastability is actively maintained (MetastabilityEngine)
    INV-6: NMOs modulate, don't compute — orchestrator writes prediction to SPS
    INV-7: All transitions logged (RegimeManager emits events)
    INV-8: Learning is phase-gated (plasticity_gate from types.py constant)
    """

    def __init__(
        self,
        state_dim: int = 64,
        hidden_dim: int = 128,
        device: str = "cpu",
        seed: int = 42,
    ):
        super().__init__()
        self.state_dim = state_dim
        self.n_nmo = 6

        # Seed for reproducibility
        torch.manual_seed(seed)

        # --- Shared Predictive State ---
        self.sps = SharedPredictiveState(
            sensory_dim=state_dim,
            internal_dim=state_dim // 2,
            goal_dim=state_dim // 2,
            n_nmo=self.n_nmo,
            device=device,
        )

        # --- Six Neuromodulatory Operators ---
        self.operators: Dict[str, NeuromodulatoryOperator] = {}
        op_classes = [
            DopamineOperator,
            AcetylcholineOperator,
            NorepinephrineOperator,
            SerotoninOperator,
            lambda sd=state_dim, hd=hidden_dim: GABAOperator(sd, hd, self.n_nmo),
            GlutamateOperator,
        ]
        for cls in op_classes:
            if callable(cls) and not isinstance(cls, type):
                op = cls()
            else:
                op = cls(state_dim=state_dim, hidden_dim=hidden_dim)
            self.operators[op.nmo_type.value] = op

        # Build write-permission map (INV-1: each NMO writes only designated fields)
        self._write_permissions: Dict[str, List[str]] = {
            name: op.get_write_fields() for name, op in self.operators.items()
        }

        # Register as nn.Module children for parameter tracking
        self._op_modules = nn.ModuleDict({k: v for k, v in self.operators.items()})

        # --- Competition Dynamics ---
        self.competition = LotkaVolterraField(n_operators=self.n_nmo)
        self.kuramoto = KuramotoCoupling(n_oscillators=self.n_nmo)
        self.metastability = MetastabilityEngine(self.kuramoto)

        # --- Regime Manager ---
        self.regime_mgr = RegimeManager()

        # --- Operator name → index mapping ---
        self._op_names = list(self.operators.keys())
        self._op_index = {name: i for i, name in enumerate(self._op_names)}

        # --- Audit log ---
        self._audit: deque[DNCAAudit] = deque(maxlen=5000)
        self._step_count = 0

    def step(
        self,
        sensory_input: torch.Tensor,
        reward: float = 0.0,
        goal: Optional[torch.Tensor] = None,
    ) -> DNCStepOutput:
        """
        Execute one full DNCA cycle.

        Sequence (INV-2 enforced: DAC runs first, modulations write after):
        1. SPS receives sensory input + input validation
        2. Active NMOs run DAC cycles (INV-2: dominant forms, acceptor predicts)
        3. All NMOs compute modulations (read-only SPS snapshot)
        4. Phase-locked write to SPS (INV-1: only permitted fields)
        5. CompetitionField step (Lotka-Volterra)
        6. Kuramoto phase coupling step
        7. MetastabilityEngine check (INV-5)
        8. Forward model learning (INV-8: phase-gated)
        9. Regime lifecycle check (INV-7: transitions logged)
        10. Phase advance + plasticity gate
        """
        self._step_count += 1

        # === 1. Input validation + SPS receives input ===
        if sensory_input.dim() == 0 or sensory_input.shape[-1] == 0:
            raise ValueError(f"sensory_input must be non-empty, got shape {sensory_input.shape}")
        if not torch.isfinite(sensory_input).all():
            raise ValueError("sensory_input contains NaN or Inf")

        self.sps.receive_sensory(sensory_input)
        if goal is not None:
            self.sps.goal = goal.detach().clone()
        self.sps.reward_context = torch.tensor([reward]).expand(self.sps.dims["reward_dim"])

        # === 2. Active NMOs run DAC cycles FIRST (INV-2) ===
        # Dominant forms and acceptor predicts BEFORE modulations are applied.
        # Use previous step's activities to determine which NMOs are active.
        dominant_idx = self.competition.get_dominant_index()
        dominant_name = self._op_names[dominant_idx]
        dominant_op = self.operators[dominant_name]
        dominant_activity = float(self.competition.activities[dominant_idx].item())

        mismatch = 0.0
        satiation = 0.0
        for i, (name, op) in enumerate(self.operators.items()):
            if self.competition.activities[i] > ACTIVITY_THRESHOLD:
                motivation = 1.0 if name == dominant_name else 0.5
                dac_out = op.step_dac(
                    sensory_input,
                    goal_hint=self.sps.goal if goal is not None else None,
                    motivation=motivation,
                )
                if name == dominant_name:
                    mismatch = dac_out.mismatch_normed
                    satiation = dac_out.satiation
                    # INV-6: orchestrator writes prediction to SPS, not the NMO
                    self.sps.sensory_prediction = dac_out.prediction.detach().clone()
                    self.sps.prediction_error = (
                        sensory_input.detach() - dac_out.prediction.detach()
                    )

        # === 3. All NMOs compute modulations (read-only snapshot) ===
        snapshot = self.sps.snapshot()
        modulations: Dict[str, Dict[str, torch.Tensor]] = {}
        growth_rates = torch.zeros(self.n_nmo)
        natural_freqs = torch.zeros(self.n_nmo)

        for i, (name, op) in enumerate(self.operators.items()):
            modulations[name] = op.modulate(snapshot)
            growth_rates[i] = op.compute_growth_rate(snapshot)
            natural_freqs[i] = op.get_natural_frequency()

        # Validate growth rates are finite
        if not torch.isfinite(growth_rates).all():
            growth_rates = torch.where(
                torch.isfinite(growth_rates), growth_rates, torch.zeros_like(growth_rates)
            )

        # === 4. Phase-locked write to SPS (INV-1: only permitted fields) ===
        for name, fields in modulations.items():
            permitted = self._write_permissions.get(name, [])
            for field_name, value in fields.items():
                if field_name in permitted and hasattr(self.sps, field_name):
                    setattr(self.sps, field_name, value.detach().clone())

        # === 5. Competition field step ===
        activities = self.competition.step(growth_rates)
        self.sps.nmo_activities = activities.clone()
        for i, name in enumerate(self._op_names):
            self.operators[name].activity = float(activities[i].item())

        # === 6. Kuramoto coupling step ===
        r = self.kuramoto.step(activities, natural_freqs)
        self.sps.regime_coherence = torch.tensor([r])

        # === 7. MetastabilityEngine check (INV-5) ===
        self.metastability.check()

        # === 8. Forward model learning — dual fast/slow (INV-8: phase-gated) ===
        # Fast learning: gate > -0.5 (broad window, ~75% of theta cycle)
        # Slow learning: gate > 0.5 (theta peak only, ~25% of cycle)
        gate_val = float(self.sps.plasticity_gate.item())
        if gate_val > -0.5 and self._step_count > 1:
            # Fast lr for broad gate, slow lr for peak-only consolidation
            lr = FORWARD_MODEL_LR if gate_val <= 0.5 else FORWARD_MODEL_LR * 0.1
            n_steps = FORWARD_MODEL_INNER_STEPS if gate_val <= 0.5 else FORWARD_MODEL_INNER_STEPS * 2
            for i, (name, op) in enumerate(self.operators.items()):
                if activities[i] <= ACTIVITY_THRESHOLD:
                    continue
                dac = op.dac
                if dac._prev_prediction is not None and dac._goal is not None:
                    # Use smoothed target to reduce noise
                    target = dac.get_learning_target(dac.encoder(sensory_input.float()).detach())
                    for _ in range(n_steps):
                        enc = dac.encoder(sensory_input.float())
                        pi = torch.cat([enc, dac._goal.detach()], dim=-1)
                        pred = dac.forward_model(pi)
                        loss = torch.nn.functional.mse_loss(pred, target)
                        loss.backward()
                        with torch.no_grad():
                            for p in list(dac.forward_model.parameters()) + list(dac.encoder.parameters()):
                                if p.grad is not None:
                                    p.data -= lr * p.grad
                                    p.grad.zero_()

        # === 9. Regime lifecycle check (INV-7) ===
        # Update dominant from new activities (after competition step)
        dominant_idx = self.competition.get_dominant_index()
        dominant_name = self._op_names[dominant_idx]
        dominant_activity = float(activities[dominant_idx].item())

        sorted_acts = activities.sort(descending=True)
        challenger_activity = float(sorted_acts.values[1].item()) if self.n_nmo > 1 else 0.0

        ne_op = self.operators.get("norepinephrine")
        ne_reset = hasattr(ne_op, 'reset_triggered') and ne_op.reset_triggered
        if ne_reset:
            self.competition.inject_reset(dominant_idx)

        transition = self.regime_mgr.update(
            dominant_nmo=dominant_name,
            dominant_activity=dominant_activity,
            dominant_satiation=satiation,
            dominant_mismatch=mismatch,
            coherence=r,
            ne_reset=ne_reset,
            challenger_activity=challenger_activity,
            goal=self.sps.goal,
        )

        # === 10. Phase advance + plasticity gate (INV-8) ===
        self.sps.update_phase(dt=25.0)  # 25ms per step

        # Get regime info
        regime = self.regime_mgr.current
        regime_phase = regime.phase.name if regime else "NONE"
        regime_age = regime.age if regime else 0

        # === Audit (INV-7 support) ===
        audit = DNCAAudit(
            step=self._step_count,
            activities={name: float(activities[i].item()) for i, name in enumerate(self._op_names)},
            dominant_nmo=dominant_name,
            regime_phase=regime_phase,
            regime_age=regime_age,
            r_mean=self.kuramoto.r_mean,
            r_std=self.kuramoto.r_std,
            coupling_K=self.kuramoto.K,
            mismatch=mismatch,
            satiation=satiation,
            plasticity_gate=float(self.sps.plasticity_gate.item()),
            theta_phase=float(self.sps.theta_phase.item()),
        )
        self._audit.append(audit)

        return DNCStepOutput(
            dominant_nmo=dominant_name,
            dominant_activity=dominant_activity,
            all_activities={name: float(activities[i].item()) for i, name in enumerate(self._op_names)},
            regime_phase=regime_phase,
            regime_age=regime_age,
            r_order=r,
            r_std=self.kuramoto.r_std,
            mismatch=mismatch,
            satiation=satiation,
            plasticity_gate=float(self.sps.plasticity_gate.item()),
            theta_phase=float(self.sps.theta_phase.item()),
            transition_event=transition,
            step=self._step_count,
        )

    def run(
        self,
        inputs: List[torch.Tensor],
        rewards: Optional[List[float]] = None,
        goal: Optional[torch.Tensor] = None,
    ) -> List[DNCStepOutput]:
        """Run DNCA over sequence of inputs."""
        return [
            self.step(inp, rewards[i] if rewards else 0.0, goal)
            for i, inp in enumerate(inputs)
        ]

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "step": self._step_count,
            "regime": {
                "current": self.regime_mgr.current.dominant_nmo if self.regime_mgr.current else None,
                "phase": self.regime_mgr.current.phase.name if self.regime_mgr.current else "NONE",
                "total_transitions": self.regime_mgr.transition_count,
                "durations": self.regime_mgr.get_regime_durations()[-10:],
            },
            "metastability": {
                "r_mean": self.kuramoto.r_mean,
                "r_std": self.kuramoto.r_std,
                "K": self.kuramoto.K,
            },
            "competition": {
                "activities": {name: self.operators[name].activity for name in self._op_names},
                "concentration": self.competition.get_dominant_concentration(),
            },
            "sps": {
                "mismatch": float(self.sps.prediction_error.norm().item()),
                "plasticity_gate": float(self.sps.plasticity_gate.item()),
                "theta_phase": float(self.sps.theta_phase.item()),
            },
        }

    def save_checkpoint(self, path: str) -> None:
        """Save full DNCA state for reproducible resumption."""
        torch.save({
            "step_count": self._step_count,
            "state_dict": self.state_dict(),
            "competition_activities": self.competition.activities.clone(),
            "kuramoto_phases": self.kuramoto.phases.clone(),
            "kuramoto_K": self.kuramoto.K,
        }, path)

    def load_checkpoint(self, path: str) -> None:
        """Load saved DNCA state."""
        payload = torch.load(path, map_location="cpu", weights_only=False)
        self.load_state_dict(payload["state_dict"])
        self._step_count = payload["step_count"]
        self.competition.activities = payload["competition_activities"]
        self.kuramoto.phases = payload["kuramoto_phases"]
        self.kuramoto.K = payload["kuramoto_K"]

    def reset(self) -> None:
        self.sps.reset()
        for op in self.operators.values():
            op.reset()
        self.competition.reset()
        self.kuramoto.reset()
        self.metastability.reset()
        self.regime_mgr.reset()
        self._audit.clear()
        self._step_count = 0
