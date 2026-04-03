"""
BN-Syn Spiking Neural Criticality — Real Substrate Adapter
===========================================================
Critical branching network with emergent 1/f dynamics.
Implements DomainAdapter Protocol.

Physics: N neurons with sparse random connectivity (k synapses each).
Transmission probability p = 1/k gives branching ratio σ = p·k = 1.
At σ=1: avalanches follow P(s)~s^{-3/2}, population rate shows 1/f PSD.

The 1/f statistics EMERGE from the critical branching process.
No synthetic 1/f noise is generated anywhere.

Mapping:
  topo = windowed population firing rate (activity level)
  cost = windowed rate CV (temporal variability)
  At criticality: higher rate → lower relative variability → cost ~ topo^(-γ)

Universality class: mean-field directed percolation.
Theoretical prediction: γ ≈ 1.0 at σ = 1 (Beggs & Plenz 2003).
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

_N_NEURONS = 200
_K_CONNECTIONS = 10
_TOPO_FLOOR = 1e-6
_SIM_STEPS = 10000
_WINDOW = 50


class BnSynAdapter:
    """Critical branching process neural network.

    Full network simulation: N neurons, k random connections each,
    transmission probability p = 1/k → branching ratio σ = 1.
    Population firing rate and rate CV are computed in sliding windows.
    """

    def __init__(self, seed: int = 42, N: int = _N_NEURONS, k: int = _K_CONNECTIONS) -> None:
        self._rng = np.random.default_rng(seed)
        self._N = N
        self._k = k
        self._p_transmit = 1.0 / k  # σ = p·k = 1.0

        # Build sparse random connectivity
        self._targets: list[np.ndarray] = []
        for i in range(N):
            pool = np.delete(np.arange(N), i)
            targets = self._rng.choice(pool, size=min(k, N - 1), replace=False)
            self._targets.append(targets)

        # Simulate full network dynamics
        self._pop_rates = self._simulate()
        self._t = 0
        self._window = _WINDOW

    def _simulate(self) -> np.ndarray:
        """Simulate critical branching network, return population rate per timestep.

        Vectorized: uses connectivity matrix for fast propagation.
        """
        N = self._N
        T = _SIM_STEPS
        pop_rate = np.zeros(T)

        # Build dense connectivity matrix for vectorized propagation
        # conn[i, j] = 1 if neuron i → neuron j
        conn = np.zeros((N, N), dtype=np.float32)
        for i, tgts in enumerate(self._targets):
            conn[i, tgts] = 1.0

        p_spontaneous = 0.002
        active = np.zeros(N, dtype=bool)
        active[self._rng.choice(N, size=5, replace=False)] = True

        for t in range(T):
            pop_rate[t] = float(np.sum(active)) / N

            # Vectorized propagation: active neurons fire through connections
            # input_strength[j] = number of active presynaptic neurons for j
            input_strength = conn[active].sum(axis=0) if active.any() else np.zeros(N)

            # Each input transmits with probability p_transmit independently
            # P(at least one transmits) = 1 - (1 - p)^n ≈ n*p for small n*p
            transmit_prob = 1.0 - (1.0 - self._p_transmit) ** input_strength
            next_active = self._rng.random(N) < transmit_prob

            # Spontaneous firing
            next_active |= self._rng.random(N) < p_spontaneous

            # Refractory
            next_active &= ~active
            active = next_active

        return pop_rate

    def _window_stats(self) -> tuple[float, float]:
        """Compute mean rate and CV for current window."""
        t = self._t % (len(self._pop_rates) - self._window)
        window = self._pop_rates[t:t + self._window]
        mean_rate = float(np.mean(window))
        if mean_rate < 1e-10:
            return 1e-6, 1.0
        cv = float(np.std(window) / mean_rate)
        return mean_rate, cv

    @property
    def domain(self) -> str:
        return "spike"

    @property
    def state_keys(self) -> List[str]:
        return ["firing_rate", "rate_cv", "branching_ratio"]

    def state(self) -> Dict[str, float]:
        self._t += 20
        rate, cv = self._window_stats()
        return {
            "firing_rate": rate,
            "rate_cv": cv,
            "branching_ratio": self._p_transmit * self._k,
        }

    def topo(self) -> float:
        """Windowed population firing rate (activity level)."""
        rate, _ = self._window_stats()
        return max(_TOPO_FLOOR, rate)

    def thermo_cost(self) -> float:
        """Windowed rate CV (temporal variability).

        At criticality: higher rate → lower relative variability.
        This is the emergent 1/f signature of the branching process.
        """
        _, cv = self._window_stats()
        return max(_TOPO_FLOOR, cv)

    def get_all_pairs(self) -> tuple[np.ndarray, np.ndarray]:
        """Return all (topo, cost) pairs from full simulation."""
        step = 10
        topos, costs = [], []
        for start in range(0, len(self._pop_rates) - self._window, step):
            window = self._pop_rates[start:start + self._window]
            mean_rate = float(np.mean(window))
            if mean_rate > _TOPO_FLOOR:
                cv = float(np.std(window) / mean_rate)
                if cv > _TOPO_FLOOR:
                    topos.append(mean_rate)
                    costs.append(cv)
        return np.array(topos), np.array(costs)


def validate_standalone() -> dict:
    from scipy.stats import theilslopes

    print("=== BN-Syn Critical Branching Network — Validation ===\n")
    adapter = BnSynAdapter(seed=42)
    topos, costs = adapter.get_all_pairs()

    log_t, log_c = np.log(topos), np.log(costs)
    slope, intc, lo, hi = theilslopes(log_c, log_t)
    gamma = -slope
    yhat = slope * log_t + intc
    ss_r = np.sum((log_c - yhat) ** 2)
    ss_t = np.sum((log_c - log_c.mean()) ** 2)
    r2 = 1 - ss_r / ss_t if ss_t > 1e-10 else 0

    dist = abs(gamma - 1.0)
    regime = (
        "METASTABLE" if dist < 0.15 else
        "WARNING" if dist < 0.30 else
        "CRITICAL" if dist < 0.50 else "COLLAPSE"
    )

    print(f"  Windows: {len(topos)}")
    print(f"  σ = {adapter._p_transmit * adapter._k:.2f} (branching ratio)")
    print(f"  γ = {gamma:.4f}  R² = {r2:.4f}  CI = [{-hi:.3f}, {-lo:.3f}]")
    print(f"  Regime = {regime}")

    return {"gamma": round(float(gamma), 4), "r2": round(float(r2), 4),
            "ci": [round(float(-hi), 4), round(float(-lo), 4)],
            "n": len(topos), "regime": regime}


if __name__ == "__main__":
    validate_standalone()
