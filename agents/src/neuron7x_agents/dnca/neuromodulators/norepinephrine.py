"""
Norepinephrine Operator — Adaptive Gain / Mode Switching / Reset.

Two modes (Aston-Jones & Cohen 2005):
  PHASIC: gain ↑, sigmoid sharpened, WTA → exploitation
  TONIC: gain ↓, sigmoid flattened, soft competition → exploration

Network reset trigger (Bouret & Sara 2005):
  P(context_change | observations) > RESET_THRESHOLD → collapse current dominant

Unexpected uncertainty (Yu & Dayan 2005):
  NE signals the probability that the environmental context has changed.

Writes: gain_modulation, context_change_signal
"""

from __future__ import annotations

import math
from typing import Dict, List

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType, NEMode


class NorepinephrineOperator(NeuromodulatoryOperator):
    """NE operator: adaptive gain, mode switching, network reset."""

    RESET_THRESHOLD = 0.7

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__(
            nmo_type=NMOType.NE,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=1.5,  # fast, responsive
        )
        # Context change detector
        self.context_net = nn.Sequential(
            nn.Linear(state_dim * 2, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )
        self._mode: NEMode = NEMode.PHASIC
        self._context_change_prob: float = 0.0
        self._pe_baseline: float = 0.0
        self._pe_history: List[float] = []

    @property
    def mode(self) -> NEMode:
        return self._mode

    @property
    def reset_triggered(self) -> bool:
        return self._context_change_prob > self.RESET_THRESHOLD

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Compute gain modulation and context change probability."""
        sensory = sps.get("sensory", torch.zeros(self.state_dim))
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))

        # Context change detection
        with torch.no_grad():
            ctx_input = torch.cat([sensory.float(), pe.float()])
            self._context_change_prob = self.context_net(ctx_input).item()

        # Track prediction error for mode selection
        pe_mag = pe.norm().item()
        self._pe_history.append(pe_mag)
        if len(self._pe_history) > 50:
            self._pe_history = self._pe_history[-50:]

        # Mode selection: high sustained PE → tonic (explore), low PE → phasic (exploit)
        if len(self._pe_history) > 10:
            recent_mean = sum(self._pe_history[-10:]) / 10
            if recent_mean > self._pe_baseline * 1.5 + 0.5:
                self._mode = NEMode.TONIC
            else:
                self._mode = NEMode.PHASIC
            self._pe_baseline = 0.95 * self._pe_baseline + 0.05 * recent_mean

        # Gain modulation
        if self._mode == NEMode.PHASIC:
            gain = 1.5  # sharp sigmoid, exploitation
        else:
            gain = 0.5  # flat sigmoid, exploration

        return {
            "gain_modulation": torch.tensor([gain]),
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """NE growth: high when context change is detected or PE is unusual."""
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        pe_mag = pe.norm().item() / (1.0 + pe.norm().item())
        return 0.2 + self._context_change_prob * 0.5 + pe_mag * 0.3

    def get_write_fields(self) -> list[str]:
        return ["gain_modulation"]

    def reset(self) -> None:
        super().reset()
        self._mode = NEMode.PHASIC
        self._context_change_prob = 0.0
        self._pe_baseline = 0.0
        self._pe_history.clear()
