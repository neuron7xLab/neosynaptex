"""
GABA Operator — Competition Normalization / Stabilization.

Primary computation: Divisive normalization (Carandini & Heeger 2012)
  R_i = D_i^n / (σ^n + Σ_j D_j^n)
  Canonical neural computation underlying competition.

High GABA → hard categorical selection between regimes
Low GABA → overlapping, blended regime states

Writes: normalization_field
GABA does NOT select regimes; it sets the selection resolution.
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType


class GABAOperator(NeuromodulatoryOperator):
    """GABA operator: divisive normalization of competition."""

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128, n_nmo: int = 6):
        super().__init__(
            nmo_type=NMOType.GABA,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=0.7,
        )
        self.n_nmo = n_nmo
        self._sigma = 0.5  # semi-saturation constant
        self._exponent = 2.0  # sharpness

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Apply divisive normalization to NMO activity field."""
        activities = sps.get("nmo_activities", torch.zeros(self.n_nmo))

        # R_i = D_i^n / (σ^n + Σ_j D_j^n)
        D = activities.float().clamp(min=0.0)
        D_pow = D.pow(self._exponent)
        denom = self._sigma ** self._exponent + D_pow.sum()
        normalized = D_pow / (denom + 1e-8)

        return {
            "normalization_field": normalized,
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """GABA growth: high when competition is unresolved (many active NMOs)."""
        activities = sps.get("nmo_activities", torch.zeros(self.n_nmo))
        # Entropy of activity distribution
        probs = activities.float().clamp(min=1e-8)
        probs = probs / probs.sum()
        entropy = -(probs * probs.log()).sum().item()
        max_entropy = torch.tensor(float(self.n_nmo)).log().item()
        return 0.45 + (entropy / max(max_entropy, 1e-8)) * 0.4

    def get_write_fields(self) -> list[str]:
        return ["normalization_field"]
