"""
Glutamate Operator — Activation / Plasticity / Error Amplification.

Primary computation: NMDA coincidence detection → Ca²⁺ → LTP/LTD
  High Ca²⁺ (CF + PF coincidence) → LTP (Δw > 0)
  Moderate Ca²⁺ (PF alone) → LTD (Δw < 0)

Error amplification: forward connections carry prediction errors
  (superficial pyramidal cells → higher areas)

NMDA dendritic spikes: contextual multiplicative gain
  → multitask capability (Bhatt et al. 2023)

Writes: plasticity_gate, prediction_error (amplified)
"""

from __future__ import annotations

import math
from typing import Dict

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType


class GlutamateOperator(NeuromodulatoryOperator):
    """Glu operator: excitation, plasticity, error amplification."""

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__(
            nmo_type=NMOType.GLU,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=1.0,
        )
        # Error amplification: context-dependent gain on prediction error
        self.error_gain = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 4),
            nn.GELU(),
            nn.Linear(hidden_dim // 4, state_dim),
            nn.Sigmoid(),
        )

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Amplify prediction errors and compute plasticity gate."""
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        theta_phase = sps.get("theta_phase", torch.zeros(1))
        sensory = sps.get("sensory", torch.zeros(self.state_dim))

        # Context-dependent error amplification (NMDA dendritic spike analog)
        with torch.no_grad():
            gain = self.error_gain(sensory.float())
            amplified_pe = pe.float() * (1.0 + gain)

        # Plasticity gate: cos(theta_phase) — LTP at peak, LTD at trough (INV-8)
        phase = theta_phase.item() if theta_phase.dim() == 0 else theta_phase[0].item()
        plast = math.cos(phase)

        return {
            "prediction_error": amplified_pe,
            "plasticity_gate": torch.tensor([plast]),
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """Glu growth: high when prediction errors are large (learning needed)."""
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        pe_mag = pe.norm().item() / (1.0 + pe.norm().item())
        return 0.40 + pe_mag * 0.5

    def get_write_fields(self) -> list[str]:
        return ["prediction_error", "plasticity_gate"]
