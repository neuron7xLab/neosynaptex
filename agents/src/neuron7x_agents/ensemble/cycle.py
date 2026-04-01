"""
RegulatoryCycle — the atomic unit of the Neuromodulatory Cognitive Ensemble.

Each cycle is an autonomous Dominant-Acceptor loop with:
- Its own dominant (goal attractor)
- Its own acceptor (prediction → comparison → mismatch/satiation)
- A characteristic neuromodulatory profile (DA/NE/ACh/5-HT balance)
- A regulatory function (salience, focus, inhibition, etc.)

The cycle competes with other cycles for the cognitive workspace
through Ukhtomsky-style monopolistic dynamics. The winning cycle
dictates system behavior until it saturates or is displaced.

This is NOT an agent with a role. This is a MODE OF REGULATION.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class RegulatoryFunction(Enum):
    """
    Eight regulatory principles — each is a distinct mode of
    cognitive control, not a persona or tool.
    """
    SALIENCE = auto()        # what matters right now (DA↑ NE↑)
    FOCUS = auto()           # sustain on one target (ACh↑ DA→)
    ACTIVATION = auto()      # mobilize resources (NE↑ DA↑)
    INHIBITION = auto()      # stop, wait, be patient (5-HT↑ GABA↑)
    SWITCHING = auto()       # release current, seek new (NE burst, DA↓)
    MEMORY = auto()          # encode, retrieve (ACh↑ theta↑)
    CONSOLIDATION = auto()   # replay, stabilize (ACh↓ sharp-wave)
    ADAPTATION = auto()      # update models (DA RPE, climbing fiber)


@dataclass(frozen=True, slots=True)
class RegulatoryProfile:
    """
    Neuromodulatory signature of a regulatory cycle.

    Each profile defines the DA/NE/ACh/5-HT balance that characterizes
    the cycle's mode of operation. These are NOT arbitrary — they map
    to known neuromodulator-function relationships.
    """
    function: RegulatoryFunction
    dopamine: float      # [0,1] reward prediction, motivation
    norepinephrine: float  # [0,1] arousal, alertness, reset
    acetylcholine: float   # [0,1] attention, memory encoding
    serotonin: float       # [0,1] patience, behavioral inhibition

    @property
    def activation_energy(self) -> float:
        """How much drive this profile provides."""
        return (self.dopamine + self.norepinephrine) / 2.0

    @property
    def persistence(self) -> float:
        """How long this mode tends to maintain dominance."""
        return (1.0 + self.acetylcholine * 2.0) * (1.0 - self.norepinephrine * 0.5)

    @property
    def exploration_bias(self) -> float:
        """Tendency to explore vs exploit."""
        return self.norepinephrine - self.dopamine * 0.5 + 0.5

    def as_tensor(self) -> torch.Tensor:
        return torch.tensor([
            self.dopamine, self.norepinephrine,
            self.acetylcholine, self.serotonin,
        ], dtype=torch.float32)


# === Canonical profiles (neurobiologically grounded) ===

CANONICAL_PROFILES = {
    RegulatoryFunction.SALIENCE: RegulatoryProfile(
        function=RegulatoryFunction.SALIENCE,
        dopamine=0.8, norepinephrine=0.7, acetylcholine=0.3, serotonin=0.2,
    ),
    RegulatoryFunction.FOCUS: RegulatoryProfile(
        function=RegulatoryFunction.FOCUS,
        dopamine=0.5, norepinephrine=0.2, acetylcholine=0.9, serotonin=0.4,
    ),
    RegulatoryFunction.ACTIVATION: RegulatoryProfile(
        function=RegulatoryFunction.ACTIVATION,
        dopamine=0.7, norepinephrine=0.8, acetylcholine=0.4, serotonin=0.1,
    ),
    RegulatoryFunction.INHIBITION: RegulatoryProfile(
        function=RegulatoryFunction.INHIBITION,
        dopamine=0.2, norepinephrine=0.1, acetylcholine=0.3, serotonin=0.9,
    ),
    RegulatoryFunction.SWITCHING: RegulatoryProfile(
        function=RegulatoryFunction.SWITCHING,
        dopamine=0.3, norepinephrine=0.9, acetylcholine=0.2, serotonin=0.2,
    ),
    RegulatoryFunction.MEMORY: RegulatoryProfile(
        function=RegulatoryFunction.MEMORY,
        dopamine=0.4, norepinephrine=0.3, acetylcholine=0.9, serotonin=0.5,
    ),
    RegulatoryFunction.CONSOLIDATION: RegulatoryProfile(
        function=RegulatoryFunction.CONSOLIDATION,
        dopamine=0.3, norepinephrine=0.1, acetylcholine=0.1, serotonin=0.7,
    ),
    RegulatoryFunction.ADAPTATION: RegulatoryProfile(
        function=RegulatoryFunction.ADAPTATION,
        dopamine=0.9, norepinephrine=0.5, acetylcholine=0.5, serotonin=0.3,
    ),
}


class RegulatoryCycle(nn.Module):
    """
    One autonomous Dominant-Acceptor cycle with a regulatory profile.

    This is the atomic unit of the ensemble. It:
    1. Encodes input through its regulatory lens (profile-gated)
    2. Maintains a dominant (goal attractor) specific to its function
    3. Predicts outcomes via its own forward model
    4. Compares predictions with reality (acceptor)
    5. Competes for workspace access via strength signal
    6. Yields control when saturated

    The cycle does NOT know about other cycles. Competition happens
    at the workspace level through the ensemble orchestrator.
    """

    def __init__(
        self,
        profile: RegulatoryProfile,
        state_dim: int = 64,
        hidden_dim: int = 128,
    ):
        super().__init__()
        self.profile = profile
        self.state_dim = state_dim

        # Profile-gated encoder: modulates input based on neuromod signature
        self.encoder = nn.Sequential(
            nn.Linear(state_dim + 4, hidden_dim),  # +4 for neuromod profile
            nn.GELU(),
            nn.Linear(hidden_dim, state_dim),
            nn.LayerNorm(state_dim),
        )

        # Forward model: predicts next state given current + action
        self.forward_model = nn.Sequential(
            nn.Linear(state_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, state_dim),
        )

        # Strength estimator: how relevant is this cycle right now?
        self.strength_net = nn.Sequential(
            nn.Linear(state_dim + 4, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

        # Action proposal: what this cycle wants to do
        self.action_head = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, state_dim),
        )

        self._init_weights()

        # Cycle state
        self.dominant_strength: float = 0.0
        self.age: int = 0
        self.mismatch_history: List[float] = []
        self._prev_prediction: Optional[torch.Tensor] = None
        self._satiation: float = 0.0

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def encode(self, state: torch.Tensor) -> torch.Tensor:
        """Encode input through this cycle's regulatory lens."""
        profile_vec = self.profile.as_tensor().to(state.device)
        x = torch.cat([state.float(), profile_vec], dim=-1)
        return self.encoder(x)

    @torch.no_grad()
    def compute_strength(self, state: torch.Tensor) -> float:
        """How much this cycle wants to be active right now."""
        profile_vec = self.profile.as_tensor().to(state.device)
        x = torch.cat([state.float(), profile_vec], dim=-1)
        raw = self.strength_net(x).item()
        # Modulate by profile activation energy
        self.dominant_strength = raw * self.profile.activation_energy
        return self.dominant_strength

    def predict(self, encoded_state: torch.Tensor) -> torch.Tensor:
        """Predict next state (acceptor formation — BEFORE action)."""
        # Use previous prediction as context (or zeros)
        if self._prev_prediction is not None:
            context = self._prev_prediction
        else:
            context = torch.zeros_like(encoded_state)
        x = torch.cat([encoded_state, context], dim=-1)
        pred = self.forward_model(x)
        self._prev_prediction = pred.detach().clone()
        return pred

    def propose_action(self, encoded_state: torch.Tensor) -> torch.Tensor:
        """What this cycle wants the system to do."""
        return self.action_head(encoded_state)

    def compare(self, predicted: torch.Tensor, actual: torch.Tensor) -> Dict[str, float]:
        """
        Acceptor comparison: predicted vs actual.
        Returns mismatch, satiation delta, orienting signal.
        """
        mismatch_vec = actual.detach() - predicted.detach()
        mismatch = float(mismatch_vec.norm().item())
        # Normalize by state dim
        normed = mismatch / (1.0 + mismatch)

        self.mismatch_history.append(normed)
        if len(self.mismatch_history) > 50:
            self.mismatch_history = self.mismatch_history[-50:]

        # Satiation accumulates when mismatch is low (predictions are good)
        if normed < 0.3:
            self._satiation += 0.01 * self.profile.persistence
        else:
            self._satiation *= 0.95

        # Orienting: surprise relative to recent history
        if len(self.mismatch_history) > 5:
            recent_mean = sum(self.mismatch_history[-10:]) / min(10, len(self.mismatch_history))
            recent_std = max(0.01, (sum((x - recent_mean)**2 for x in self.mismatch_history[-10:]) / min(10, len(self.mismatch_history))) ** 0.5)
            z = (normed - recent_mean) / recent_std
            orienting = max(0.0, min(1.0, (z - 1.0) / 2.0))
        else:
            orienting = 0.0

        self.age += 1

        return {
            "mismatch": normed,
            "satiation": self._satiation,
            "orienting": orienting,
            "age": self.age,
        }

    @property
    def is_saturated(self) -> bool:
        """Has this cycle achieved its goal and should yield?"""
        return self._satiation > 0.8

    def reset(self) -> None:
        self.dominant_strength = 0.0
        self.age = 0
        self.mismatch_history.clear()
        self._prev_prediction = None
        self._satiation = 0.0
