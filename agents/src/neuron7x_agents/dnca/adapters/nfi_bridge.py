"""
NFI BN-Syn Adapter — DNCA as BN-Syn layer in NFI architecture.

NFI architecture (Vasylenko 2026):
  ML-SDM → CA1-LAM → BN-Syn → MFN⁺

BN-Syn = physically grounded spiking dynamics.
DNCA qualifies because:
  - Kuramoto oscillatory dynamics
  - Competitive neuromodulatory field
  - γ_DNCA = +1.285 (same scale as biological systems)

KEY INVARIANT: γ is DERIVED from trajectory, never stored as parameter.
NFI INV-1: γ is emergent, not a parameter.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from neuron7x_agents.dnca.probes.gamma_probe import BNSynGammaProbe


@dataclass(slots=True)
class NFIStateContract:
    """Minimal NFI contract — what BN-Syn receives from CA1-LAM."""
    field_sequence: np.ndarray   # shape [T, state_dim] or [state_dim]
    modulation: float = 1.0      # tau_control from CA1-LAM
    step_id: int = 0


@dataclass(slots=True)
class BNSynOutput:
    """What BN-Syn returns to NFI."""
    dominant_coherence: float       # Kuramoto r(t)
    pac_strength: float             # theta-gamma PAC proxy
    prediction_error: np.ndarray    # DAC mismatch vector
    gamma_estimate: Optional[float] # γ from recent trajectory (None if < 200 steps)
    insight_signal: float           # sudden mismatch drop
    dominant_nmo: str               # which NMO is currently dominant
    regime_age: int                 # steps in current regime


class NFIBNSynAdapter:
    """
    Adapts DNCA as BN-Syn layer in NFI.

    γ is DERIVED here — computed every gamma_interval steps from
    the recent trajectory window. Never stored as a parameter.
    This satisfies NFI INV-1: γ is emergent.
    """

    def __init__(
        self,
        dnca: Any,
        probe: Optional[BNSynGammaProbe] = None,
        gamma_interval: int = 50,
        gamma_window: int = 200,
    ):
        self.dnca = dnca
        self.probe = probe or BNSynGammaProbe(window_size=50, n_bootstrap=100)
        self.gamma_interval = gamma_interval
        self.gamma_window = gamma_window

        self._trajectory: deque = deque(maxlen=gamma_window + 50)
        self._step_count = 0
        self._current_gamma: Optional[float] = None
        self._gamma_history: List[float] = []

    def step(self, contract: NFIStateContract) -> BNSynOutput:
        """
        Process one NFI step.

        1. Convert NFI contract → DNCA sensory input
        2. Run DNCA.step()
        3. Every gamma_interval steps: compute γ from recent trajectory
        4. Return BNSynOutput with γ as derived field
        """
        self._step_count += 1

        # Convert NFI field_sequence to sensory input
        field = contract.field_sequence
        if field.ndim > 1:
            sensory = torch.from_numpy(field[-1]).float()
        else:
            sensory = torch.from_numpy(field).float()

        # Modulation from CA1-LAM affects input gain
        sensory = sensory * contract.modulation

        # Ensure dimension matches
        sd = self.dnca.state_dim
        if sensory.shape[-1] != sd:
            padded = torch.zeros(sd)
            n = min(sensory.shape[-1], sd)
            padded[:n] = sensory[:n]
            sensory = padded

        # Run DNCA
        out = self.dnca.step(sensory, reward=0.0)

        # Record for γ computation
        self._trajectory.append({
            "step": self._step_count,
            "nmo_activities": np.array([out.all_activities[k] for k in sorted(out.all_activities.keys())]),
            "dominant_nmo": out.dominant_nmo,
            "mismatch": out.mismatch,
            "prediction_error": self.dnca.sps.prediction_error.detach().cpu().numpy().copy(),
        })

        # Compute γ periodically (DERIVED, not stored)
        if self._step_count % self.gamma_interval == 0 and len(self._trajectory) >= self.gamma_window:
            traj_list = list(self._trajectory)[-self.gamma_window:]
            images = self.probe.trajectory_to_images_nmo(traj_list)
            if images.shape[0] > 10:
                pe0, beta0 = self.probe.compute_tda_series(images)
                report = self.probe.compute_gamma(pe0, beta0, "bnsyn_live")
                self._current_gamma = report.gamma
                self._gamma_history.append(report.gamma)

        # Insight: mismatch drop > 30% in last 5 steps
        insight = 0.0
        if len(self._trajectory) > 5:
            recent_mm = [t["mismatch"] for t in list(self._trajectory)[-5:]]
            if len(recent_mm) >= 5 and recent_mm[0] > 0.01:
                drop = (recent_mm[0] - recent_mm[-1]) / recent_mm[0]
                if drop > 0.3:
                    insight = min(1.0, drop)

        return BNSynOutput(
            dominant_coherence=out.r_order,
            pac_strength=out.r_order * out.dominant_activity,
            prediction_error=self.dnca.sps.prediction_error.detach().cpu().numpy().copy(),
            gamma_estimate=self._current_gamma,
            insight_signal=insight,
            dominant_nmo=out.dominant_nmo or "none",
            regime_age=out.regime_age,
        )

    @property
    def current_gamma(self) -> Optional[float]:
        """γ from last computation. None if < gamma_window steps."""
        return self._current_gamma

    @property
    def gamma_history(self) -> List[float]:
        return list(self._gamma_history)

    def reset(self) -> None:
        self.dnca.reset()
        self._trajectory.clear()
        self._step_count = 0
        self._current_gamma = None
        self._gamma_history.clear()
