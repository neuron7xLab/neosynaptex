"""
Minimal CA1 network scaffold for quick API validation.

This is a lightweight, deterministic placeholder that produces synthetic
activity suitable for smoke tests. It is not a biophysical simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np


@dataclass
class SimulationResult:
    time: np.ndarray
    spikes: np.ndarray
    voltages: np.ndarray
    weights: np.ndarray


class CA1Network:
    """
    Deterministic scaffold of a CA1 network.

    The goal is to provide a stable public API for quick-start examples and
    regression tests. The generated signals are synthetic but reproducible for
    a given seed.
    """

    def __init__(self, N: int, seed: int = 42, dt: float = 0.1):
        if N <= 0:
            raise ValueError("N must be positive")
        self.N = N
        self.dt = float(dt)
        self._rng = np.random.default_rng(seed)
        # Pre-sample a base weight matrix to keep results deterministic
        base = self._rng.lognormal(mean=0.0, sigma=0.1, size=(N, N))
        np.fill_diagonal(base, 0.0)
        self._weights = base.astype(float)
        self._last_result: Optional[SimulationResult] = None

    def simulate(self, duration_ms: int, dt: Optional[float] = None) -> Dict[str, np.ndarray]:
        """Run a lightweight stochastic simulation.

        Args:
            duration_ms: total simulated time in milliseconds.
            dt: optional timestep override (ms).

        Returns:
            dict with keys: time, spikes, voltages, weights.
        """
        step = float(dt) if dt is not None else self.dt
        if step <= 0:
            raise ValueError("dt must be positive")

        time = np.arange(0, duration_ms, step, dtype=float)
        # Use a low firing probability for synthetic spikes
        p_fire = 0.02
        spikes = self._rng.random((time.size, self.N)) < p_fire
        # Voltages are simple noisy baseline values
        voltages = -65.0 + self._rng.normal(scale=3.0, size=(time.size, self.N))
        # Keep weights constant during this minimal simulation
        weights = self._weights.copy()

        self._last_result = SimulationResult(
            time=time, spikes=spikes, voltages=voltages, weights=weights
        )
        return {
            "time": time,
            "spikes": spikes,
            "voltages": voltages,
            "weights": weights,
        }

    def plot_activity(self):
        """
        Plot spike raster if matplotlib is available.

        Raises:
            RuntimeError: when matplotlib is not installed.
        """
        if self._last_result is None:
            raise RuntimeError("No simulation data available. Call simulate() first.")

        try:
            import matplotlib.pyplot as plt  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised via tests for error path
            raise RuntimeError(
                "matplotlib is required for plotting. Install via `pip install matplotlib`."
            ) from exc

        spikes = self._last_result.spikes
        t = self._last_result.time

        spike_times, neuron_ids = np.nonzero(spikes)
        plt.eventplot(
            positions=t[spike_times],
            lineoffsets=neuron_ids,
            linelengths=0.8,
            colors="black",
        )
        plt.xlabel("Time (ms)")
        plt.ylabel("Neuron ID")
        plt.title("CA1Network synthetic spike raster")
        plt.tight_layout()
        return plt
