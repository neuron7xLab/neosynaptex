"""
SharedPredictiveState (SPS) — the only communication channel between NMOs.

INV-1: SPS is the only shared resource.
NMOs do not call each other directly.
NMOs do not share parameters.
All coordination happens through SPS fields.

Implementation: typed tensor dictionary with field-level access control,
phase-locked write gating, and complete state snapshots for replay.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import torch


# Default dimensions
_DEFAULTS = {
    "sensory_dim": 64,
    "internal_dim": 32,
    "goal_dim": 32,
    "reward_dim": 8,
    "n_nmo": 6,
    "n_gamma": 7,
    "wm_slots": 7,
    "item_dim": 32,
}


class SharedPredictiveState:
    """
    Continuous shared workspace — typed tensor dictionary.

    All fields are continuous (no binaries except consolidation_flag).
    No field is owned by a single operator.
    All operators read; each writes only to designated fields.

    Access rules:
    - READ: any NMO can read any field
    - WRITE: each NMO writes only to its designated output fields
    - CONFLICT: phase-locked temporal gating (NMOs write in theta sub-phases)
    """

    def __init__(
        self,
        sensory_dim: int = 64,
        internal_dim: int = 32,
        goal_dim: int = 32,
        reward_dim: int = 8,
        n_nmo: int = 6,
        n_gamma: int = 7,
        wm_slots: int = 7,
        item_dim: int = 32,
        device: str = "cpu",
    ):
        self.dims = {
            "sensory_dim": sensory_dim,
            "internal_dim": internal_dim,
            "goal_dim": goal_dim,
            "reward_dim": reward_dim,
            "n_nmo": n_nmo,
            "n_gamma": n_gamma,
            "wm_slots": wm_slots,
            "item_dim": item_dim,
        }
        self.device = device

        # --- Sensory subspace ---
        self.sensory = torch.zeros(sensory_dim, device=device)
        self.sensory_prediction = torch.zeros(sensory_dim, device=device)
        self.prediction_error = torch.zeros(sensory_dim, device=device)
        self.precision_weights = torch.ones(sensory_dim, device=device)

        # --- Internal state subspace ---
        self.internal = torch.zeros(internal_dim, device=device)
        self.goal = torch.zeros(goal_dim, device=device)
        self.value_estimate = torch.zeros(1, device=device)

        # --- Phase / oscillatory subspace ---
        self.theta_phase = torch.zeros(1, device=device)
        self.gamma_phase = torch.zeros(n_gamma, device=device)
        self.pac_coherence = torch.zeros(1, device=device)

        # --- Reward / motivational subspace ---
        self.reward_context = torch.zeros(reward_dim, device=device)
        self.dopamine_signal = torch.zeros(1, device=device)
        self.valence = torch.zeros(1, device=device)
        self.temporal_discount = torch.tensor([0.99], device=device)

        # --- Competition / regime subspace ---
        self.nmo_activities = torch.zeros(n_nmo, device=device)
        self.regime_coherence = torch.zeros(1, device=device)
        self.dominant_id: int = -1
        self.dominant_age: int = 0
        self.competition_energy = torch.zeros(n_nmo, device=device)

        # --- Memory subspace ---
        self.working_memory = torch.zeros(wm_slots, item_dim, device=device)
        self.retrieval_result = torch.zeros(item_dim, device=device)
        self.consolidation_flag: bool = False

        # --- Modulation subspace ---
        self.gain_modulation = torch.ones(1, device=device)
        self.normalization_field = torch.ones(n_nmo, device=device) / n_nmo
        self.plasticity_gate = torch.zeros(1, device=device)
        self.inhibition_signal = torch.zeros(1, device=device)

        # --- Step counter ---
        self.step_count: int = 0

    def receive_sensory(self, sensory: torch.Tensor) -> None:
        """New sensory input arrives."""
        self.sensory = sensory.detach().clone().to(self.device)
        self.step_count += 1

    def update_phase(self, dt: float = 1.0) -> None:
        """Advance theta phase and compute plasticity gate. INV-8."""
        self.theta_phase += 2.0 * math.pi * 6.0 * dt / 1000.0  # 6 Hz, dt in ms
        self.theta_phase = self.theta_phase % (2.0 * math.pi)
        # LTP at peak (0°), LTD at trough (180°)
        self.plasticity_gate = torch.cos(self.theta_phase)

    def snapshot(self) -> Dict[str, Any]:
        """Complete state snapshot for replay and debugging.

        All tensor fields are returned as cloned tensors (not scalars)
        so that NMO operators can call .item(), .dim(), .float(), etc.
        """
        return {
            "sensory": self.sensory.clone(),
            "prediction_error": self.prediction_error.clone(),
            "precision_weights": self.precision_weights.clone(),
            "goal": self.goal.clone(),
            "value_estimate": self.value_estimate.clone(),
            "theta_phase": self.theta_phase.clone(),
            "pac_coherence": self.pac_coherence.clone(),
            "dopamine_signal": self.dopamine_signal.clone(),
            "valence": self.valence.clone(),
            "temporal_discount": self.temporal_discount.clone(),
            "reward_context": self.reward_context.clone(),
            "nmo_activities": self.nmo_activities.clone(),
            "regime_coherence": self.regime_coherence.clone(),
            "dominant_id": self.dominant_id,
            "dominant_age": self.dominant_age,
            "gain_modulation": self.gain_modulation.clone(),
            "plasticity_gate": self.plasticity_gate.clone(),
            "inhibition_signal": self.inhibition_signal.clone(),
            "step": self.step_count,
        }

    def as_flat_tensor(self) -> torch.Tensor:
        """Flatten key fields into a single tensor for neural net input."""
        return torch.cat([
            self.sensory,
            self.prediction_error,
            self.goal,
            self.nmo_activities,
            self.dopamine_signal,
            self.valence,
            self.gain_modulation,
            self.plasticity_gate,
            self.inhibition_signal,
            self.regime_coherence,
        ]).detach()

    def reset(self) -> None:
        """Reset all fields to initial state."""
        for attr in vars(self):
            val = getattr(self, attr)
            if isinstance(val, torch.Tensor):
                val.zero_()
        self.precision_weights.fill_(1.0)
        self.temporal_discount.fill_(0.99)
        self.gain_modulation.fill_(1.0)
        n = self.dims["n_nmo"]
        self.normalization_field = torch.ones(n, device=self.device) / n
        self.dominant_id = -1
        self.dominant_age = 0
        self.consolidation_flag = False
        self.step_count = 0
