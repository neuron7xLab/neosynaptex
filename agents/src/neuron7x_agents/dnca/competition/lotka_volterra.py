"""
Lotka-Volterra Winnerless Competition — Stable Heteroclinic Channels.

dA_i/dt = A_i · (σ_i − Σ_j ρ_ij · A_j) + ξ_i

Key property: asymmetric ρ_ij ≠ ρ_ji produces structurally stable
heteroclinic channels (SHC) where trajectories visit saddle equilibria
in reproducible sequence. No single NMO permanently wins.

Encoding capacity: e·(N-1)! for N operators.

Reference: Rabinovich et al. 2001, Phys. Rev. Lett. 87:068102
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import torch


class LotkaVolterraField:
    """
    Generalized Lotka-Volterra competition with asymmetric inhibition.

    INV-4: No NMO permanently wins. The competition is winnerless.
    Achieved through asymmetric ρ_ij coupling and noise injection.
    """

    def __init__(
        self,
        n_operators: int = 6,
        dt: float = 0.02,
        noise_scale: float = 0.02,
    ):
        self.n = n_operators
        self.dt = dt
        self.noise_scale = noise_scale

        # Asymmetric inhibition matrix (ρ_ij ≠ ρ_ji)
        # Biologically calibrated: GABA hard to suppress, Glu fires on PE,
        # DA/ACh/NE moderate mutual inhibition.
        # Operator order: DA(0), ACh(1), NE(2), 5-HT(3), GABA(4), Glu(5)
        GABA_IDX = 4
        GLU_IDX = 5
        self.rho = torch.zeros(n_operators, n_operators)
        for i in range(n_operators):
            for j in range(n_operators):
                if i == j:
                    # Higher self-inhibition for GABA/Glu (prevent monopoly)
                    self.rho[i, j] = 1.6 if i in (GABA_IDX, GLU_IDX) else 1.0
                elif j == GABA_IDX:
                    # GABA hard to suppress: ρ(any→GABA) = 0.3
                    self.rho[i, j] = 0.3
                elif j == GLU_IDX:
                    # Glu fires when PE high: ρ(any→Glu) = 0.2
                    self.rho[i, j] = 0.2
                elif i == GABA_IDX:
                    # GABA strongly inhibits others: ρ(GABA→any) = 1.2
                    self.rho[i, j] = 1.2
                elif i in (0, 1, 2, 3) and j in (0, 1, 2, 3):
                    # DA/ACh/NE/5-HT mutual: ρ = 0.8-1.0
                    self.rho[i, j] = 0.9
                else:
                    self.rho[i, j] = 0.8

        # Activity vector
        self.activities = torch.ones(n_operators) * 0.1

    def step(
        self,
        growth_rates: torch.Tensor,
        external_perturbation: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Integrate one LV timestep.

        Args:
            growth_rates: σ_i for each operator (from compute_growth_rate)
            external_perturbation: optional direct activity modification

        Returns:
            Updated activity vector A_i ∈ [0, 1]
        """
        A = self.activities
        sigma = growth_rates.float()

        # Compress growth rates to prevent monopoly from rate imbalance
        # Preserves rank order but narrows the range (winnerless competition)
        sigma_mean = sigma.mean()
        sigma = sigma_mean + (sigma - sigma_mean) * 0.3

        # dA_i/dt = A_i · (σ_i − Σ_j ρ_ij · A_j) + ξ_i
        inhibition = self.rho @ A
        dA = A * (sigma - inhibition) * self.dt

        # Noise: prevents deadlock, maintains exploration
        noise = torch.randn(self.n) * self.noise_scale * self.dt

        # Fatigue: dominant operator slowly loses energy (INV-4 enforcement)
        # This forces regime transitions even when growth rates are asymmetric
        dominant_idx = A.argmax()
        fatigue = torch.zeros(self.n)
        fatigue[dominant_idx] = -0.002 * A[dominant_idx]  # proportional fatigue
        A = A + dA + noise + fatigue

        # External perturbation (e.g., NE reset)
        if external_perturbation is not None:
            A = A + external_perturbation

        # Clamp to [0, 1]
        self.activities = A.clamp(0.0, 1.0)
        return self.activities.clone()

    def get_dominant_index(self) -> int:
        """Index of currently strongest operator."""
        return int(self.activities.argmax().item())

    def get_dominant_concentration(self) -> float:
        """max(A_i) / sum(A_i) — how concentrated is dominance?"""
        total = self.activities.sum().item()
        if total < 1e-8:
            return 0.0
        return float(self.activities.max().item() / total)

    def inject_reset(self, target_idx: Optional[int] = None) -> None:
        """NE-triggered reset: collapse specific or dominant operator."""
        if target_idx is not None:
            self.activities[target_idx] *= 0.1
        else:
            dominant = self.get_dominant_index()
            self.activities[dominant] *= 0.1
        # Boost noise temporarily
        self.activities += torch.randn(self.n) * 0.05

    def reset(self) -> None:
        self.activities = torch.ones(self.n) * 0.1
