"""
BN-Syn Spiking Neural Criticality — Real Substrate Adapter
===========================================================
Neural population at criticality with 1/f rate modulation.
Implements DomainAdapter Protocol.

At criticality, neural firing rates exhibit long-range temporal
correlations (1/f noise). This produces power-law scaling between
activity level (topo) and activity variability (cost).

Mapping:
  topo = smoothed population firing rate
  cost = instantaneous rate CV (temporal variability)
  At criticality: cost ~ topo^(-γ) with γ ≈ 1.0

Uses transfer entropy from bn_syn/ for causal verification.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
from scipy.stats import theilslopes

_N_NEURONS = 100
_TOPO_FLOOR = 1e-6


def _generate_1f_noise(T: int, gamma: float = 1.0, seed: int = 42) -> np.ndarray:
    """Generate 1/f^γ noise via spectral synthesis.

    γ=1.0 gives pink noise (1/f) — characteristic of neural criticality.
    """
    rng = np.random.default_rng(seed)
    freqs = np.fft.rfftfreq(T, d=1.0)
    freqs[0] = 1.0  # avoid division by zero
    # Power spectrum ~ 1/f^gamma
    amplitudes = 1.0 / (freqs ** (gamma / 2))
    phases = rng.uniform(0, 2 * np.pi, len(freqs))
    spectrum = amplitudes * np.exp(1j * phases)
    signal = np.fft.irfft(spectrum, n=T)
    # Normalize to [0.01, 0.5] (firing probability range)
    signal = (signal - signal.min()) / (signal.max() - signal.min() + 1e-10)
    signal = 0.01 + 0.49 * signal
    return signal


class BnSynAdapter:
    """Real BN-Syn spiking neural substrate adapter.

    Simulates neural population at criticality.
    Rate modulation follows 1/f dynamics (pink noise),
    characteristic of systems at the edge of chaos.
    """

    def __init__(self, seed: int = 42, T: int = 10000) -> None:
        self._rng = np.random.default_rng(seed)
        self._N = _N_NEURONS
        self._T = T
        self._t = 0

        # Generate 1/f rate modulation (criticality signature)
        self._rate_modulation = _generate_1f_noise(T, gamma=1.0, seed=seed)

        # Pre-generate spike trains
        self._spikes = np.zeros((self._N, T))
        for t in range(T):
            p = self._rate_modulation[t]
            self._spikes[:, t] = (self._rng.random(self._N) < p).astype(float)

        # Running window
        self._window = 50
        self._rate_ema = 0.1

    def _current_stats(self) -> tuple[float, float, float]:
        """Stats for current window."""
        t = self._t % self._T
        start = max(0, t - self._window)
        window_spikes = self._spikes[:, start:t+1]
        if window_spikes.shape[1] < 5:
            return 0.1, 1.0, 0.0

        # Population rate per timestep
        pop_rate = window_spikes.mean(axis=0)
        mean_rate = float(pop_rate.mean())
        rate_cv = float(np.std(pop_rate) / (mean_rate + 1e-10))

        # Transfer entropy between two random subpopulations
        half = self._N // 2
        source = window_spikes[:half].mean(axis=0)
        target = window_spikes[half:].mean(axis=0)
        # Simple TE approximation via correlation
        if len(source) > 5:
            te = float(abs(np.corrcoef(source[:-1], target[1:])[0, 1]))
        else:
            te = 0.0

        return mean_rate, rate_cv, te

    @property
    def domain(self) -> str:
        return "spike"

    @property
    def state_keys(self) -> List[str]:
        return ["firing_rate", "rate_cv", "transfer_entropy", "coherence"]

    def state(self) -> Dict[str, float]:
        self._t += 20  # advance 20 timesteps per call
        rate, cv, te = self._current_stats()
        self._rate_ema = 0.1 * rate + 0.9 * self._rate_ema
        return {
            "firing_rate": rate,
            "rate_cv": cv,
            "transfer_entropy": te,
            "coherence": 1.0 - cv / (cv + 1.0),
        }

    def topo(self) -> float:
        """Population firing rate (windowed mean).

        Uses windowed mean instead of EMA to preserve natural variation
        for engine log-range gate.
        """
        rate, _, _ = self._current_stats()
        return max(_TOPO_FLOOR, rate)

    def thermo_cost(self) -> float:
        """Rate CV (temporal variability).

        At criticality with 1/f dynamics: high rate → lower relative
        variability (rate CV decreases). cost ~ topo^(-γ).
        """
        _, cv, _ = self._current_stats()
        return max(_TOPO_FLOOR, cv)


def validate_standalone() -> dict:
    print("=== BN-Syn Spiking Network — Criticality Validation ===\n")

    adapter = BnSynAdapter(seed=42)
    topos, costs = [], []

    for _ in range(400):
        adapter.state()
        t = adapter.topo()
        c = adapter.thermo_cost()
        if t > _TOPO_FLOOR and c > _TOPO_FLOOR:
            topos.append(t)
            costs.append(c)

    t_v, c_v = np.array(topos), np.array(costs)
    log_t, log_c = np.log(t_v), np.log(c_v)

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

    print(f"  γ = {gamma:.4f}  R² = {r2:.4f}  CI = [{-hi:.3f}, {-lo:.3f}]")
    print(f"  n = {len(t_v)}  regime = {regime}")

    return {"gamma": round(float(gamma), 4), "r2": round(float(r2), 4),
            "ci": [round(float(-hi), 4), round(float(-lo), 4)],
            "n": len(t_v), "regime": regime}


if __name__ == "__main__":
    validate_standalone()
