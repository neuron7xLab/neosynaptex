"""Lotka-Volterra competition dynamics substrate adapter.

Generalized competitive exclusion with N species. At the edge of
competitive exclusion (winnerless competition), the system exhibits
metastable heteroclinic orbits. Topo = species diversity (Shannon H),
cost = extinction rate. γ ≈ 1.0 when competition is balanced.

Reference: Rabinovich et al. (2001) PRL 87:068102 — winnerless competition.
"""

from __future__ import annotations

import math

import numpy as np


class LotkaVolterraAdapter:
    """DomainAdapter for ecological competition dynamics."""

    def __init__(
        self,
        n_species: int = 6,
        carrying_capacity: float = 100.0,
        dt: float = 0.01,
        noise: float = 0.02,
        seed: int = 88,
    ) -> None:
        self._n = n_species
        self._k = carrying_capacity
        self._dt = dt
        self._noise = noise
        self._rng = np.random.default_rng(seed)
        self._t = 0

        # Initial populations
        self._pop = self._rng.uniform(10, 50, n_species)

        # Growth rates (slightly different per species)
        self._r = 0.5 + 0.1 * self._rng.standard_normal(n_species)

        # Interaction matrix: moderate competition, asymmetric
        self._alpha = np.eye(n_species)
        for i in range(n_species):
            for j in range(n_species):
                if i != j:
                    self._alpha[i, j] = 0.6 + 0.3 * self._rng.random()

    @property
    def domain(self) -> str:
        return "lotka_volterra"

    @property
    def state_keys(self) -> list[str]:
        return ["shannon_h", "dominance", "turnover"]

    def state(self) -> dict[str, float]:
        self._t += 1
        self._step()

        return {
            "shannon_h": self._shannon_h(),
            "dominance": self._dominance(),
            "turnover": self._turnover(),
        }

    def topo(self) -> float:
        """Topological complexity = effective number of species × log connectivity.

        exp(H) gives effective number of species (Jost 2006).
        Multiplied by log of interaction density for organizational complexity.
        """
        h = self._shannon_h()
        effective_n = math.exp(h) if h > 0 else 1.0
        # Interaction density: fraction of non-zero interactions
        interaction_density = np.sum(self._alpha > 0.1) / self._n**2
        return max(0.01, effective_n * math.log(1 + interaction_density * self._n))

    def thermo_cost(self) -> float:
        """Thermodynamic cost = population flux / total biomass.

        High flux relative to biomass = energetically costly dynamics.
        At competitive equilibrium: low flux. At chaos: high flux.
        """
        total = float(np.sum(self._pop))
        if total < 1e-6:
            return 0.01
        # Approximate flux from growth rates
        dpop = self._compute_dpop()
        flux = float(np.sum(np.abs(dpop)))
        return max(0.01, flux / total)

    def _step(self) -> None:
        """Generalized Lotka-Volterra step with noise."""
        dpop = self._compute_dpop()
        noise = self._noise * self._rng.standard_normal(self._n) * self._pop
        self._pop = np.clip(self._pop + dpop * self._dt + noise * math.sqrt(self._dt), 0.1, 1e6)

    def _compute_dpop(self) -> np.ndarray:
        """dN_i/dt = r_i * N_i * (1 - sum_j(alpha_ij * N_j) / K)."""
        competition = self._alpha @ self._pop
        return self._r * self._pop * (1.0 - competition / self._k)

    def _shannon_h(self) -> float:
        """Shannon diversity index."""
        total = float(np.sum(self._pop))
        if total < 1e-6:
            return 0.0
        p = self._pop / total
        p = p[p > 1e-10]
        return float(-np.sum(p * np.log(p)))

    def _dominance(self) -> float:
        """Berger-Parker dominance: max(p_i)."""
        total = float(np.sum(self._pop))
        if total < 1e-6:
            return 1.0
        return float(np.max(self._pop) / total)

    def _turnover(self) -> float:
        """Population turnover rate: std(growth_rates) / mean(pop)."""
        dpop = self._compute_dpop()
        mean_pop = float(np.mean(self._pop))
        if mean_pop < 1e-6:
            return 0.0
        return float(np.std(dpop) / mean_pop)
