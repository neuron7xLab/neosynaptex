"""
NeuromodulatoryOperator (NMO) — base class for all six operators.

Each NMO has:
- A unique regulatory principle
- A DominantAcceptorCycle as its computational base unit
- A neuromodulatory profile
- An activity scalar A_i ∈ [0, 1]

INV-6: Each NMO modulates, does not compute.
NMOs modify how SPS is processed, not what the final answer is.
There is no "output NMO" that produces the system's response.
The system's behavior emerges from SPS state after all NMOs have modulated it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.dac import DACOutput, DominantAcceptorCycle
from neuron7x_agents.dnca.core.types import NMOType


class NeuromodulatoryOperator(nn.Module, ABC):
    """
    Abstract base for all neuromodulatory operators.

    Subclasses implement:
    - modulate(): read SPS fields, compute modulation, return fields to write
    - compute_growth_rate(): σ_i for Lotka-Volterra competition
    - get_natural_frequency(): ω_k for Kuramoto coupling
    - get_write_fields(): which SPS fields this operator writes to
    """

    def __init__(
        self,
        nmo_type: NMOType,
        state_dim: int = 64,
        hidden_dim: int = 128,
        natural_frequency: float = 1.0,
    ):
        super().__init__()
        self.nmo_type = nmo_type
        self.state_dim = state_dim
        self._natural_frequency = natural_frequency

        # Every NMO has its own DAC
        self.dac = DominantAcceptorCycle(state_dim=state_dim, hidden_dim=hidden_dim)

        # Activity scalar
        self.activity: float = 0.0

        # Phase for Kuramoto coupling
        self.phase: float = 0.0

    @property
    def name(self) -> str:
        return self.nmo_type.value

    def get_natural_frequency(self) -> float:
        return self._natural_frequency

    def step_dac(
        self, sensory: torch.Tensor, goal_hint: torch.Tensor | None = None,
        motivation: float = 1.0,
    ) -> DACOutput:
        """Run this operator's internal DAC cycle."""
        return self.dac.step(sensory, goal_hint, motivation)

    @abstractmethod
    def modulate(self, sps_snapshot: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Read SPS snapshot, compute modulation, return fields to write.

        INV-6: Returns MODULATED FIELDS, not final outputs.
        The returned dict keys must be in get_write_fields().
        """
        ...

    @abstractmethod
    def compute_growth_rate(self, sps_snapshot: Dict[str, torch.Tensor]) -> float:
        """
        Compute σ_i: how much this NMO "wants" to be active right now.
        Used by Lotka-Volterra competition field.
        """
        ...

    @abstractmethod
    def get_write_fields(self) -> list[str]:
        """Which SPS fields this operator is allowed to write."""
        ...

    def reset(self) -> None:
        self.dac.reset()
        self.activity = 0.0
        self.phase = 0.0
