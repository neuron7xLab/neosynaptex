"""
Environment Operator — Field of Concern Expansion (Levin 2019).

"Intelligence scales with the size of the problem solved for."
— Michael Levin

This 7th NMO extends DNCA's field of concern beyond self-regulation.
It models the external environment and other agents, producing
environment_prediction and environment_error signals.

If γ(expanded) > γ(self_only), then γ is a measure of field of concern.

Writes: environment_prediction (via SPS.internal), environment_error
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType


class EnvironmentOperator(NeuromodulatoryOperator):
    """
    Models external environment dynamics.

    Biological analog: hippocampal place cells + entorhinal grid cells
    that maintain a model of external space independent of self-state.

    Reference: Levin M. (2019) "The Computational Boundary of a Self"
    """

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__(
            nmo_type=NMOType.GLU,  # Reuse GLU type as closest analog
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=0.9,
        )
        # Override type to custom string (not in enum but works as dict key)
        self._custom_type = "environment"

        # Environment model: predicts next environment state from current
        self.env_model = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, state_dim),
        )
        # Other-agent model: simplified theory of mind
        self.agent_model = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 8),  # compact agent representation
        )

        self._prev_env_pred: torch.Tensor | None = None
        self._env_error_history: list[float] = []

        for m in list(self.env_model.modules()) + list(self.agent_model.modules()):
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    @property
    def name(self) -> str:
        return "environment"

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Predict environment next state, compute environment error."""
        sensory = sps.get("sensory", torch.zeros(self.state_dim))

        with torch.no_grad():
            env_pred = self.env_model(sensory.float())
            agent_repr = self.agent_model(sensory.float())

        # Environment prediction error (if we had a previous prediction)
        env_error = torch.zeros(1)
        if self._prev_env_pred is not None:
            err = (sensory.detach() - self._prev_env_pred.detach()).norm()
            env_error = err.unsqueeze(0)
            self._env_error_history.append(float(err.item()))
            if len(self._env_error_history) > 100:
                self._env_error_history = self._env_error_history[-100:]

        self._prev_env_pred = env_pred.detach().clone()

        # Write to internal state (environment model extends internal representation)
        return {
            "internal": env_pred[:self.state_dim // 2] if env_pred.shape[0] >= self.state_dim // 2 else env_pred,
        }

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """Environment operator grows when external prediction error is high."""
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        pe_mag = pe.norm().item() / (1.0 + pe.norm().item())
        # Also grows when environment is changing (high variance in recent errors)
        if len(self._env_error_history) > 5:
            recent = self._env_error_history[-10:]
            var = sum((x - sum(recent) / len(recent)) ** 2 for x in recent) / len(recent)
            env_change = min(1.0, var * 5.0)
        else:
            env_change = 0.2
        return 0.35 + pe_mag * 0.3 + env_change * 0.2

    def get_write_fields(self) -> list[str]:
        return ["internal"]

    def reset(self) -> None:
        super().reset()
        self._prev_env_pred = None
        self._env_error_history.clear()
