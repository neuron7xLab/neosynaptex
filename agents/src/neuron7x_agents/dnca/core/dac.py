"""
DominantAcceptorCycle (DAC) — the base computational unit inside every NMO.

Combines:
- Dominant (Ukhtomsky 1923): winner-take-all attractor with active inhibition.
  The dominant RECRUITS unrelated signals toward its goal.
  The dominant SUPPRESSES competing attractors via lateral inhibition.
  The dominant exhibits INERTIA — persists after original stimulus is gone.

- Acceptor of Action Result (Anokhin 1968): forward model of expected outcome
  formed BEFORE the action executes, evaluated against motivational criteria.
  Mismatch between predicted and actual result = prediction error = obstacle.

INV-2: The Dominant forms BEFORE the Acceptor predicts.
INV-3: Prediction error is evaluated against motivational criteria.

Forward model: 3-head ensemble with inverse-variance weighted prediction.
Dual learning: fast (every open gate) + slow (theta peak only).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from neuron7x_agents.dnca.core.types import (
    CAPTURE_THRESHOLD,
    DAC_GOAL_HINT_BLEND,
    DAC_GOAL_INERTIA,
    DAC_RESIDUAL_SCALE,
    DAC_SATIATION_INCREMENT,
    DAC_SATIATION_LEARNING,
    DAC_SUMMATION_BASE,
    DAC_SUMMATION_DOMINANT_MULT,
    DAC_SUMMATION_RELEVANCE,
    DOMINANCE_THRESHOLD,
    MISMATCH_COLLAPSE,
    SATIATION_THRESHOLD,
)


@dataclass(slots=True)
class DACOutput:
    """Output of one DAC cycle."""
    encoded_state: torch.Tensor
    prediction: torch.Tensor
    prediction_error: float
    mismatch_normed: float
    satiation: float
    orienting: float
    dominant_locked: bool
    goal: torch.Tensor


class _ResidualHead(nn.Module):
    """One forward model head: output = input[:state_dim] + scale * delta."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, scale: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        )
        self.output_dim = output_dim
        self.scale = scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skip = x[..., :self.output_dim]
        delta = self.net(x) * self.scale
        return skip + delta


class _EnsembleForward(nn.Module):
    """
    3-head ensemble forward model with inverse-variance weighted prediction.

    Diverse heads via different hidden dimensions.
    Prediction = Σ(w_i * pred_i) where w_i ∝ 1/var_i.
    """

    def __init__(self, state_dim: int, hidden_dim: int, n_heads: int = 3):
        super().__init__()
        self.n_heads = n_heads
        self.state_dim = state_dim
        self.heads = nn.ModuleList([
            _ResidualHead(
                input_dim=state_dim * 2,
                hidden_dim=hidden_dim + i * (hidden_dim // 4),
                output_dim=state_dim,
                scale=DAC_RESIDUAL_SCALE,
            )
            for i in range(n_heads)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Inverse-variance weighted ensemble prediction."""
        preds = torch.stack([h(x) for h in self.heads], dim=0)  # [n_heads, state_dim]
        # Inverse-variance weighting: w_i ∝ 1 / (var_i + ε)
        if self.n_heads > 1:
            variances = preds.var(dim=0, keepdim=True).mean(dim=-1, keepdim=True)  # [1, 1]
            # Per-head deviation from mean as proxy for per-head variance
            mean_pred = preds.mean(dim=0, keepdim=True)
            head_devs = ((preds - mean_pred) ** 2).mean(dim=-1)  # [n_heads]
            weights = 1.0 / (head_devs + 1e-6)
            weights = weights / weights.sum()
            return (weights.unsqueeze(-1) * preds).sum(dim=0)
        return preds[0]

    def all_predictions(self, x: torch.Tensor) -> torch.Tensor:
        """Return all head predictions for learning. Shape: [n_heads, state_dim]."""
        return torch.stack([h(x) for h in self.heads], dim=0)


class DominantAcceptorCycle(nn.Module):
    """
    One D-A cycle with 3-head ensemble forward model.

    Biological analog: Ukhtomsky's dominant + Anokhin's acceptor.
    Each NMO contains one DAC as its computational core.

    Sequence per step (INV-2 enforced):
    1. Encode sensory input through operator's lens
    2. Dominant captures: lock goal vector from encoded input
    3. Acceptor predicts: ensemble forward model predicts BEFORE action
    4. On next step: compare prediction with actual → mismatch/satiation
    """

    def __init__(self, state_dim: int = 64, hidden_dim: int = 128):
        super().__init__()
        self.state_dim = state_dim

        # Encoder: operator-specific sensory processing
        self.encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, state_dim),
            nn.LayerNorm(state_dim),
        )

        # Dominant: goal extractor
        self.goal_encoder = nn.Sequential(
            nn.Linear(state_dim, state_dim),
            nn.Tanh(),
        )

        # Acceptor: 3-head ensemble forward model
        self.forward_model = _EnsembleForward(
            state_dim=state_dim, hidden_dim=hidden_dim, n_heads=3,
        )

        # Initialize with small weights so skip connection dominates initially
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

        # Target smoothing buffer
        self._smooth_target: Optional[torch.Tensor] = None
        self._target_smooth_alpha = 0.9  # 0.9 * actual + 0.1 * prev_prediction

        # State
        self._goal: Optional[torch.Tensor] = None
        self._prev_prediction: Optional[torch.Tensor] = None
        self._strength: float = 0.0
        self._age: int = 0
        self._satiation: float = 0.0
        self._mismatch_integral: float = 0.0
        self._mismatch_history: List[float] = [0.5] * 20

    @property
    def strength(self) -> float:
        return self._strength

    @property
    def satiation(self) -> float:
        return self._satiation

    @property
    def age(self) -> int:
        return self._age

    @property
    def goal(self) -> Optional[torch.Tensor]:
        return self._goal

    def get_learning_target(self, actual: torch.Tensor) -> torch.Tensor:
        """Smoothed target: reduces noise in learning signal."""
        if self._smooth_target is None:
            self._smooth_target = actual.detach().clone()
        else:
            self._smooth_target = (
                self._target_smooth_alpha * actual.detach()
                + (1.0 - self._target_smooth_alpha) * self._smooth_target
            )
        return self._smooth_target.clone()

    def step(
        self,
        sensory: torch.Tensor,
        goal_hint: Optional[torch.Tensor] = None,
        motivation_weight: float = 1.0,
    ) -> DACOutput:
        """
        Execute one DAC cycle.

        INV-2 enforced: dominant captures → goal locked → acceptor predicts.
        INV-3 enforced: mismatch evaluated with motivation_weight.
        """
        self._age += 1

        # 1. Encode
        encoded = self.encoder(sensory.float())

        # 2. Dominant captures: extract goal from encoded state
        goal_raw = self.goal_encoder(encoded.detach())
        if goal_hint is not None:
            goal_raw = (1.0 - DAC_GOAL_HINT_BLEND) * goal_raw + DAC_GOAL_HINT_BLEND * goal_hint.detach()
        if self._goal is None or self._strength < CAPTURE_THRESHOLD:
            self._goal = goal_raw.detach().clone()
        else:
            self._goal = (DAC_GOAL_INERTIA * self._goal + (1.0 - DAC_GOAL_INERTIA) * goal_raw.detach()).clone()

        # 3. Acceptor predicts BEFORE action (INV-2)
        pred_input = torch.cat([encoded.detach(), self._goal], dim=-1)
        prediction = self.forward_model(pred_input)

        # Update smooth target
        self.get_learning_target(encoded.detach())

        # 4. Compare with previous prediction (if exists)
        mismatch_normed = 0.0
        orienting = 0.0
        if self._prev_prediction is not None:
            pe = encoded.detach() - self._prev_prediction.detach()
            raw_mismatch = float(pe.norm().item())
            mismatch_normed = (raw_mismatch / (1.0 + raw_mismatch)) * motivation_weight
            self._mismatch_integral += raw_mismatch
            self._mismatch_history.append(mismatch_normed)
            if len(self._mismatch_history) > 100:
                self._mismatch_history = self._mismatch_history[-100:]

            if len(self._mismatch_history) > 10:
                recent = self._mismatch_history[-20:]
                mu = sum(recent) / len(recent)
                var = sum((x - mu) ** 2 for x in recent) / len(recent)
                std = max(0.01, math.sqrt(var))
                z = (mismatch_normed - mu) / std
                orienting = max(0.0, min(1.0, (z - 1.0) / 2.0))

        self._prev_prediction = prediction.detach().clone()

        # 5. Update strength dynamics
        summation = DAC_SUMMATION_BASE + DAC_SUMMATION_RELEVANCE * (1.0 - mismatch_normed)
        if self._strength >= DOMINANCE_THRESHOLD:
            summation *= DAC_SUMMATION_DOMINANT_MULT

        penalty = mismatch_normed * 0.15

        if self._strength >= DOMINANCE_THRESHOLD:
            self._satiation += DAC_SATIATION_INCREMENT
        if mismatch_normed < 0.2:
            self._satiation += DAC_SATIATION_LEARNING

        age_norm = min(self._age / 2400.0, 1.0)
        decay = 0.001 * (1.0 + age_norm)
        sat_penalty = max(0.0, self._satiation - SATIATION_THRESHOLD) * 2.0

        self._strength += summation - penalty - sat_penalty - decay
        self._strength = max(0.0, min(1.0, self._strength))

        return DACOutput(
            encoded_state=encoded.detach(),
            prediction=prediction.detach(),
            prediction_error=mismatch_normed,
            mismatch_normed=mismatch_normed,
            satiation=self._satiation,
            orienting=orienting,
            dominant_locked=self._strength >= CAPTURE_THRESHOLD,
            goal=self._goal.clone(),
        )

    @property
    def is_saturated(self) -> bool:
        return self._satiation >= SATIATION_THRESHOLD

    @property
    def is_mismatch_collapsed(self) -> bool:
        return self._mismatch_integral > MISMATCH_COLLAPSE and self._age > 200

    def reset(self) -> None:
        self._goal = None
        self._prev_prediction = None
        self._smooth_target = None
        self._strength = 0.0
        self._age = 0
        self._satiation = 0.0
        self._mismatch_integral = 0.0
        self._mismatch_history = [0.5] * 20
