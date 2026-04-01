"""
Kuramoto Phase Coupling — cross-NMO oscillatory synchronization.

dθ_k/dt = ω_k + (K/N) Σ_j sin(θ_j − θ_k) · w_kj

r(t) = |1/N Σ_k exp(i·θ_k)| ∈ [0, 1]

DNCA operates in the METASTABLE regime where r(t) fluctuates
substantially — neither fully synchronized (rigid) nor fully
incoherent (chaotic).

Reference: Acebrón et al. 2005, Rev. Mod. Phys. 77:137-185
           Tognoli & Kelso 2014, Neuron 81:35-48
"""

from __future__ import annotations

import math
from collections import deque
from typing import List, Optional

import torch


class KuramotoCoupling:
    """
    Cross-NMO Kuramoto oscillator with metastability monitoring.

    This is the SECOND Kuramoto layer in DNCA.
    (The first is within individual NMOs for theta-gamma PAC.)
    This layer couples the PHASES of different operators.
    """

    def __init__(
        self,
        n_oscillators: int = 6,
        coupling_K: float = 1.20,
        dt: float = 0.05,
        r_history_size: int = 200,
    ):
        self.n = n_oscillators
        self.K = coupling_K
        self.dt = dt

        # Phases: initialize with partial clustering (metastable seed)
        # Two clusters with noise — avoids starting at r=0 (fully incoherent)
        self.phases = torch.zeros(n_oscillators)
        for k in range(n_oscillators):
            cluster_center = 0.0 if k % 2 == 0 else math.pi * 0.8
            self.phases[k] = cluster_center + torch.randn(1).item() * 0.4
        # Natural frequencies (set by each NMO)
        self.natural_freqs = torch.ones(n_oscillators)
        # Activity-based weights: w_kj = A_k · A_j
        self.weights = torch.ones(n_oscillators, n_oscillators)

        # Order parameter history
        self._r_history: deque[float] = deque(maxlen=r_history_size)
        self._r_current: float = 0.0

    def step(
        self,
        activities: torch.Tensor,
        natural_freqs: Optional[torch.Tensor] = None,
    ) -> float:
        """
        Advance all oscillator phases by one timestep.

        Returns: current order parameter r(t).
        """
        if natural_freqs is not None:
            self.natural_freqs = natural_freqs.float()

        N = self.n
        K = self.K

        # Weight matrix: w_kj = sqrt(A_k · A_j) — responsive at low activity
        A = activities.float().clamp(min=0.0)
        self.weights = (A.unsqueeze(1) * A.unsqueeze(0)).sqrt()

        # Kuramoto update: dθ_k/dt = ω_k + (K/N) Σ_j sin(θ_j − θ_k) · w_kj
        phase_diffs = self.phases.unsqueeze(0) - self.phases.unsqueeze(1)  # θ_j - θ_k
        coupling = (K / N) * (torch.sin(phase_diffs) * self.weights).sum(dim=0)

        # Phase noise: prevents phase-locking, drives metastability
        phase_noise = torch.randn(self.n) * 0.02 * self.dt
        d_phase = (self.natural_freqs + coupling) * self.dt + phase_noise
        self.phases = (self.phases + d_phase) % (2 * math.pi)

        # Order parameter: r = |1/N Σ exp(iθ)|
        z = torch.complex(self.phases.cos(), self.phases.sin()).mean()
        self._r_current = float(z.abs().item())
        self._r_history.append(self._r_current)

        return self._r_current

    @property
    def r(self) -> float:
        """Current Kuramoto order parameter."""
        return self._r_current

    @property
    def r_mean(self) -> float:
        """Mean r over recent history."""
        if not self._r_history:
            return 0.0
        return sum(self._r_history) / len(self._r_history)

    @property
    def r_std(self) -> float:
        """Std of r over recent history — the metastability index."""
        if len(self._r_history) < 10:
            return 0.0
        mu = self.r_mean
        var = sum((x - mu) ** 2 for x in self._r_history) / len(self._r_history)
        return math.sqrt(max(0.0, var))

    def set_coupling(self, K: float) -> None:
        """MetastabilityEngine adjusts coupling strength (bounded to prevent divergence)."""
        from neuron7x_agents.dnca.core.types import COUPLING_K_MIN, COUPLING_K_MAX
        self.K = max(COUPLING_K_MIN, min(COUPLING_K_MAX, K))

    def reset(self) -> None:
        self.phases = torch.zeros(self.n)
        for k in range(self.n):
            cluster_center = 0.0 if k % 2 == 0 else math.pi * 0.8
            self.phases[k] = cluster_center + torch.randn(1).item() * 0.4
        self._r_history.clear()
        self._r_current = 0.0
