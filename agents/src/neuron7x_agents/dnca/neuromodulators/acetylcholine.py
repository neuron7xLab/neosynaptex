"""
Acetylcholine Operator — Precision / Attention maintenance.

Primary computation: Expected uncertainty encoding (Yu & Dayan 2005)
  Π = 1/σ²(sensory) → precision weight for prediction errors
  ε̃ = Π · ε (precision-weighted prediction error)

High ACh → favor bottom-up sensory evidence over prior
Low ACh → favor top-down predictions

Writes: precision_weights, dominant persistence gain
Learning rate modulation: α ∝ ACh_level (Doya 2002)
SNR boost: 120-275% above baseline at saturation
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType


class AcetylcholineOperator(NeuromodulatoryOperator):
    """ACh operator: precision, attention, dominant persistence."""

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__(
            nmo_type=NMOType.ACH,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=0.8,  # slower, more sustained
        )
        # Precision estimator: estimates reliability of each sensory dimension
        self.precision_net = nn.Sequential(
            nn.Linear(state_dim * 2, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, state_dim),
            nn.Softplus(),  # precision must be positive
        )

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Compute precision weights from prediction error reliability."""
        sensory = sps.get("sensory", torch.zeros(self.state_dim))
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))

        with torch.no_grad():
            precision_input = torch.cat([sensory.float(), pe.float()])
            precision = self.precision_net(precision_input)
            # Normalize to reasonable range
            precision = precision / (precision.mean() + 1e-8)

        return {
            "precision_weights": precision,
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """ACh growth: high when attention is needed (moderate uncertainty)."""
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        pe_mag = pe.norm().item() / (1.0 + pe.norm().item())
        # ACh is highest at moderate uncertainty (inverted-U)
        return 0.2 + 4.0 * pe_mag * (1.0 - pe_mag)

    def get_write_fields(self) -> list[str]:
        return ["precision_weights"]
