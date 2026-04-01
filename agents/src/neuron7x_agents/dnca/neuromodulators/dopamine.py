"""
Dopamine Operator — Significance / Salience.

Primary computation: Temporal difference prediction error
  δ(t) = r(t) + γ·V(s_t) − V(s_{t-1})

Asymmetric gain (Schultz 1997; Bayer & Glimcher 2005):
  Positive δ → ×5.5 amplification (burst 20-30Hz from 3-5Hz)
  Negative δ → ×1.0 (floor-limited pause)

Distributional coding (Dabney et al. 2020):
  Encodes distribution of δ, not scalar.

Writes: dopamine_signal, competition sharpness
Interaction: opponent with 5HT (appetitive vs aversive RPE)
"""

from __future__ import annotations

from typing import Dict, List

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType, POSITIVE_RPE_GAIN, NEGATIVE_RPE_GAIN


class DopamineOperator(NeuromodulatoryOperator):
    """DA operator: significance, salience, reward prediction error."""

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__(
            nmo_type=NMOType.DA,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=1.2,  # slightly faster than baseline
        )
        # Value estimator for TD error
        self.value_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1),
        )
        self._prev_value: float = 0.0
        self._rpe_history: List[float] = []

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Compute RPE with asymmetric gain, write to dopamine_signal."""
        sensory = sps.get("sensory", torch.zeros(self.state_dim))
        reward = sps.get("reward_context", torch.zeros(1))
        discount = sps.get("temporal_discount", torch.tensor([0.99]))

        # V(s_t)
        with torch.no_grad():
            current_value = self.value_net(sensory.float()).item()

        # δ(t) = r(t) + γ·V(s_t) − V(s_{t-1})
        r = reward.mean().item() if reward.dim() > 0 else reward.item()
        delta = r + discount.item() * current_value - self._prev_value

        # Asymmetric gain (Schultz 1997)
        if delta > 0:
            effective_delta = delta * POSITIVE_RPE_GAIN
        else:
            effective_delta = delta * NEGATIVE_RPE_GAIN

        # Clamp to [-1, 1] for SPS
        signal = max(-1.0, min(1.0, effective_delta))
        self._prev_value = current_value
        self._rpe_history.append(signal)
        if len(self._rpe_history) > 100:
            self._rpe_history = self._rpe_history[-100:]

        return {
            "dopamine_signal": torch.tensor([signal]),
            "valence": torch.tensor([max(-1.0, min(1.0, delta))]),
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """DA growth: high when reward context is strong or prediction error is large."""
        reward = sps.get("reward_context", torch.zeros(1))
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        r_mag = abs(reward.mean().item()) if reward.dim() > 0 else abs(reward.item())
        pe_mag = pe.norm().item() / (1.0 + pe.norm().item())
        return 0.3 + r_mag * 0.5 + pe_mag * 0.3

    def get_write_fields(self) -> list[str]:
        return ["dopamine_signal", "valence"]

    def reset(self) -> None:
        super().reset()
        self._prev_value = 0.0
        self._rpe_history.clear()
