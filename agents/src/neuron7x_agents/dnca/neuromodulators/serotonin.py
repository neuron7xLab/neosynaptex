"""
Serotonin Operator — Behavioral Inhibition / Temporal Patience.

Primary computation: Discount factor control + aversive prediction error
  γ ∝ 5HT_level (Doya 2002)
  High 5HT → high γ → long-horizon → patience
  Low 5HT → low γ → impulsivity

Opponent with DA (Daw, Kakade & Dayan 2002):
  DA codes appetitive RPE; 5HT codes aversive RPE

Writes: temporal_discount, inhibition_signal
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType


class SerotoninOperator(NeuromodulatoryOperator):
    """5-HT operator: patience, inhibition, temporal discounting."""

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__(
            nmo_type=NMOType.SHT,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=0.5,  # slow, sustained
        )
        # Risk/aversive signal detector
        self.aversive_net = nn.Sequential(
            nn.Linear(state_dim + 1, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )
        self._inhibition_level: float = 0.0

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Compute temporal discount and behavioral inhibition."""
        sensory = sps.get("sensory", torch.zeros(self.state_dim))
        da_signal = sps.get("dopamine_signal", torch.zeros(1))

        # Aversive prediction error (opponent to DA)
        with torch.no_grad():
            aversive_input = torch.cat([sensory.float(), da_signal.float()])
            aversive_signal = self.aversive_net(aversive_input).item()

        # Inhibition: high when aversive signal is high
        self._inhibition_level = 0.9 * self._inhibition_level + 0.1 * aversive_signal

        # Temporal discount: 5HT level determines patience
        # High activity → high discount → patient
        discount = 0.90 + self.activity * 0.09  # [0.90, 0.99]

        return {
            "temporal_discount": torch.tensor([discount]),
            "inhibition_signal": torch.tensor([self._inhibition_level]),
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """5HT growth: high when negative outcomes detected or patience needed."""
        da = sps.get("dopamine_signal", torch.zeros(1)).item()
        valence = sps.get("valence", torch.zeros(1)).item()
        # Opponent: grows when DA is negative (aversive context)
        aversive = max(0.0, -da) + max(0.0, -valence)
        return 0.35 + aversive * 0.5

    def get_write_fields(self) -> list[str]:
        return ["temporal_discount", "inhibition_signal"]

    def reset(self) -> None:
        super().reset()
        self._inhibition_level = 0.0
