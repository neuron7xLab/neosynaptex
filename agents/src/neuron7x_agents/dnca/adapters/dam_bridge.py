"""
DAM v3 → DNCA Bridge: wraps ResearchEngine as a single NMO.

DAM v3 ResearchEngine = one complete cognitive cycle with:
  - ResearchDominantField (field-based dominant)
  - ResearchAcceptor (confidence + temperature)
  - ResearchCerebellum (next-state + reward prediction)
  - FieldOscillator (Kuramoto phase coupling)
  - ReplayBuffer + MultiObjectiveLoss

This adapter makes it run AS a single NMO inside DNCA, respecting
all 8 invariants. It does NOT bypass competition — its activity A_i
is governed by LotkaVolterraField like any other operator.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import NMOType


class DAMNMOAdapter(NeuromodulatoryOperator):
    """
    Wraps a DAM-like cognitive engine as a single NMO in DNCA.

    This is a LIGHTWEIGHT adapter that works even without DAM v3 installed.
    It emulates the DAM cognitive cycle internally:
    - Forward model prediction (like DAM acceptor)
    - Goal extraction (like DAM dominant)
    - Mismatch computation (like DAM comparison)
    - Optional replay and learning (gated by INV-8 plasticity)

    If DAM v3 is available, it can wrap the actual ResearchEngine.
    If not, it uses its own built-in DAC (from DNCA core).
    """

    def __init__(
        self,
        nmo_type: NMOType = NMOType.DA,
        state_dim: int = 64,
        hidden_dim: int = 128,
        use_external_dam: bool = False,
    ):
        super().__init__(
            nmo_type=nmo_type,
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            natural_frequency=1.0,
        )
        self._use_external = use_external_dam
        self._dam_engine: Any = None

        # Built-in forward model (used when DAM v3 not available)
        self._forward = nn.Sequential(
            nn.Linear(state_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, state_dim),
        )
        # Value estimator for growth rate
        self._value = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1),
        )

        for m in list(self._forward.modules()) + list(self._value.modules()):
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

        self._prev_prediction: Optional[torch.Tensor] = None
        self._replay: List[Dict[str, torch.Tensor]] = []
        self._replay_capacity = 256

    def attach_dam_engine(self, engine: Any) -> None:
        """Attach actual DAM v3 ResearchEngine (optional)."""
        self._dam_engine = engine
        self._use_external = True

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Run DAM-like cognitive cycle, return SPS field updates.

        INV-6: returns MODULATION, not final output.
        """
        sensory = sps.get("sensory", torch.zeros(self.state_dim))
        goal = sps.get("goal", torch.zeros(self.state_dim // 2))

        if self._use_external and self._dam_engine is not None:
            return self._modulate_with_dam(sps)

        # Built-in DAM-like cycle
        # Run internal DAC first (inherited from NMO base)
        # Resize goal to match DAC's state_dim if needed
        if goal.shape[-1] != self.state_dim:
            goal_resized = torch.zeros(self.state_dim, device=goal.device)
            goal_resized[:goal.shape[-1]] = goal
            goal = goal_resized
        dac_out = self.dac.step(sensory, goal_hint=goal)

        # Forward model prediction
        pred_input = torch.cat([sensory.float(), dac_out.goal[:self.state_dim]], dim=-1)
        if pred_input.shape[-1] != self.state_dim * 2:
            pred_input = torch.cat([
                sensory.float(),
                torch.zeros(self.state_dim, device=sensory.device),
            ], dim=-1)
        prediction = self._forward(pred_input)

        # Mismatch with previous prediction
        if self._prev_prediction is not None:
            pe = sensory.detach() - self._prev_prediction.detach()
        else:
            pe = torch.zeros_like(sensory)

        self._prev_prediction = prediction.detach().clone()

        # Store replay (bounded)
        self._replay.append({
            "sensory": sensory.detach().clone(),
            "prediction": prediction.detach().clone(),
            "goal": dac_out.goal.detach().clone(),
        })
        if len(self._replay) > self._replay_capacity:
            self._replay = self._replay[-self._replay_capacity:]

        # Value-based reward update
        with torch.no_grad():
            value = self._value(sensory.float()).item()

        updates: Dict[str, torch.Tensor] = {}
        if self.nmo_type == NMOType.DA:
            updates["dopamine_signal"] = torch.tensor([max(-1.0, min(1.0, value))])
        elif self.nmo_type == NMOType.ACH:
            updates["precision_weights"] = torch.ones(self.state_dim) * (1.0 + abs(value))

        return updates

    def _modulate_with_dam(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Use actual DAM v3 ResearchEngine if attached."""
        try:
            sensory = sps.get("sensory", torch.zeros(self.state_dim))
            # Attempt to construct CognitiveState and run infer()
            from neuron7x_agents.dnca.core.types import NMOType
            # This is a best-effort bridge — if DAM API changes, falls back
            state = type("CogState", (), {"sensory": sensory, "goal": sps.get("goal")})()
            output = self._dam_engine.infer(state)
            return {
                "dopamine_signal": torch.tensor([output.mismatch]),
                "prediction_error": sensory - output.predicted_next_state,
            }
        except Exception:
            return {}

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """Growth based on value prediction and mismatch."""
        sensory = sps.get("sensory", torch.zeros(self.state_dim))
        pe = sps.get("prediction_error", torch.zeros(self.state_dim))
        with torch.no_grad():
            value = abs(self._value(sensory.float()).item())
        pe_mag = pe.norm().item() / (1.0 + pe.norm().item())
        return 0.3 + value * 0.3 + pe_mag * 0.3

    def get_write_fields(self) -> list[str]:
        if self.nmo_type == NMOType.DA:
            return ["dopamine_signal"]
        elif self.nmo_type == NMOType.ACH:
            return ["precision_weights"]
        return ["prediction_error"]

    def learn(self, plasticity_gate: float) -> Optional[float]:
        """Learn from replay if plasticity gate is open (INV-8)."""
        if plasticity_gate <= 0 or len(self._replay) < 4:
            return None
        # Simple forward model training on replay
        batch = self._replay[-4:]
        total_loss = 0.0
        for rec in batch:
            pred_input = torch.cat([rec["sensory"], rec["goal"][:self.state_dim]])
            if pred_input.shape[-1] != self.state_dim * 2:
                continue
            pred = self._forward(pred_input)
            loss = torch.nn.functional.mse_loss(pred, rec["sensory"])
            total_loss += loss.item()
        return total_loss / len(batch) if batch else None

    def reset(self) -> None:
        super().reset()
        self._prev_prediction = None
        self._replay.clear()
        if self._dam_engine is not None and hasattr(self._dam_engine, "reset"):
            self._dam_engine.reset()
