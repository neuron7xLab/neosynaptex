"""Resonance Map — phase-space analytics for coherence dynamics.

Task 5 deliverable.

Goal
----
Visualisation-ready analytics engine that computes and structures the data
needed for a live dashboard of the coherence state-space:

    * γ trajectory and current regime classification
    * Objection-energy trajectory
    * Coherence S(t) with ΔS sign markers
    * Bifurcation proximity detector (spectral radius → 1)
    * Time-to-diagnosis metric (how many steps to classify regime)

This module does NOT render graphics. It produces pure-data snapshots
(``ResonanceSnapshot``, ``ResonanceMap``) that any frontend (matplotlib,
plotly, streamlit, terminal) can consume.

Design notes
------------
* numpy-only; no plotting libraries.
* Frozen dataclasses for all output objects.
* Deterministic given seed.
* INV-1 compliant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
)

__all__ = [
    "ResonanceSnapshot",
    "ResonanceMap",
    "ResonanceAnalyzer",
]

FloatArray = NDArray[np.float64]

_NEAR_BIFURCATION_THRESHOLD: Final[float] = 0.95


@dataclass(frozen=True)
class ResonanceSnapshot:
    """Single-timestep analytics snapshot."""

    t: int
    s: float
    gamma: float
    e_obj: float
    sigma2: float
    delta_s: float  # S_{t} - S_{t-1} (0 for t=0)
    spectral_radius: float
    is_stable: bool
    near_bifurcation: bool  # spectral_radius > threshold
    regime: str  # "frozen", "critical", "chaotic"


@dataclass(frozen=True)
class ResonanceMap:
    """Full phase-space analytics for a trajectory.

    Attributes:
        snapshots: per-timestep analytics.
        time_to_diagnosis: number of steps until regime is first classified
            with confidence (3 consecutive steps in same regime).
        dominant_regime: most frequent regime across the trajectory.
        bifurcation_events: timesteps where ``near_bifurcation`` flips.
        s_trajectory: coherence S(t) array.
        gamma_trajectory: γ(t) array.
        e_obj_trajectory: E_obj(t) array.
        delta_s_trajectory: ΔS(t) array.
        spectral_radius_trajectory: ρ(t) array.
    """

    snapshots: tuple[ResonanceSnapshot, ...]
    time_to_diagnosis: int
    dominant_regime: str
    bifurcation_events: tuple[int, ...]
    s_trajectory: FloatArray
    gamma_trajectory: FloatArray
    e_obj_trajectory: FloatArray
    delta_s_trajectory: FloatArray
    spectral_radius_trajectory: FloatArray


def _classify_regime(gamma: float) -> str:
    """Classify operating regime from γ value.

    - frozen: γ < 0.85 (over-damped, rigid)
    - critical: 0.85 ≤ γ ≤ 1.15 (near-critical, adaptive)
    - chaotic: γ > 1.15 (under-damped, unstable)
    """
    if gamma < 0.85:
        return "frozen"
    if gamma > 1.15:
        return "chaotic"
    return "critical"


_DIAGNOSIS_WINDOW: Final[int] = 3  # consecutive steps for confident diagnosis


class ResonanceAnalyzer:
    """Compute resonance analytics for coherence trajectories.

    Usage::

        model = CoherenceStateSpace()
        analyzer = ResonanceAnalyzer(model)
        x0 = CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-3)
        rmap = analyzer.analyze(x0, n_steps=100, rng=np.random.default_rng(42))
        print(rmap.dominant_regime, rmap.time_to_diagnosis)
    """

    def __init__(self, model: CoherenceStateSpace | None = None) -> None:
        self.model: CoherenceStateSpace = model or CoherenceStateSpace()

    def analyze(
        self,
        initial: CoherenceState,
        n_steps: int,
        inputs: FloatArray | None = None,
        rng: np.random.Generator | None = None,
        bifurcation_threshold: float = _NEAR_BIFURCATION_THRESHOLD,
    ) -> ResonanceMap:
        """Run model and produce full resonance analytics.

        Args:
            initial: starting state.
            n_steps: number of steps.
            inputs: optional (n_steps, 2) input array.
            rng: RNG for stochastic noise.
            bifurcation_threshold: spectral radius threshold for
                near-bifurcation detection.

        Returns:
            ``ResonanceMap`` with all analytics.
        """
        if n_steps < 1:
            raise ValueError("n_steps must be >= 1")

        traj = self.model.rollout(initial, n_steps, inputs, rng)

        # Per-step analytics
        snapshots: list[ResonanceSnapshot] = []
        regimes: list[str] = []
        bifurcation_events: list[int] = []
        prev_near_bif = False

        for t in range(n_steps + 1):
            state = CoherenceState.from_vector(traj[t])
            delta_s = float(traj[t, 0] - traj[t - 1, 0]) if t > 0 else 0.0

            # Stability at current state
            report = self.model.stability(state)
            rho = report.spectral_radius
            near_bif = bool(rho > bifurcation_threshold)

            # Bifurcation event detection
            if t > 0 and near_bif != prev_near_bif:
                bifurcation_events.append(t)
            prev_near_bif = near_bif

            regime = _classify_regime(state.gamma)
            regimes.append(regime)

            snapshots.append(
                ResonanceSnapshot(
                    t=t,
                    s=state.S,
                    gamma=state.gamma,
                    e_obj=state.E_obj,
                    sigma2=state.sigma2,
                    delta_s=delta_s,
                    spectral_radius=rho,
                    is_stable=report.is_stable,
                    near_bifurcation=near_bif,
                    regime=regime,
                )
            )

        # Time-to-diagnosis: first index where 3 consecutive same-regime steps
        ttd = n_steps  # default: never diagnosed
        for i in range(_DIAGNOSIS_WINDOW - 1, len(regimes)):
            window = regimes[i - _DIAGNOSIS_WINDOW + 1 : i + 1]
            if len(set(window)) == 1:
                ttd = i
                break

        # Dominant regime
        unique, counts = np.unique(regimes, return_counts=True)
        dominant = str(unique[int(np.argmax(counts))])

        # Trajectory arrays
        s_traj = traj[:, 0].copy()
        g_traj = traj[:, 1].copy()
        e_traj = traj[:, 2].copy()
        ds_traj = np.zeros(n_steps + 1, dtype=np.float64)
        ds_traj[1:] = np.diff(s_traj)
        rho_traj = np.array([snap.spectral_radius for snap in snapshots], dtype=np.float64)

        return ResonanceMap(
            snapshots=tuple(snapshots),
            time_to_diagnosis=ttd,
            dominant_regime=dominant,
            bifurcation_events=tuple(bifurcation_events),
            s_trajectory=s_traj,
            gamma_trajectory=g_traj,
            e_obj_trajectory=e_traj,
            delta_s_trajectory=ds_traj,
            spectral_radius_trajectory=rho_traj,
        )

    def analyze_trajectory(
        self,
        trajectory: FloatArray,
        bifurcation_threshold: float = _NEAR_BIFURCATION_THRESHOLD,
    ) -> ResonanceMap:
        """Analyze a pre-computed trajectory (no simulation).

        Args:
            trajectory: (T, 4) state trajectory array.
            bifurcation_threshold: spectral radius threshold.

        Returns:
            ``ResonanceMap``.
        """
        if trajectory.ndim != 2 or trajectory.shape[1] != 4:
            raise ValueError(f"trajectory must have shape (T, 4), got {trajectory.shape}")
        n_steps = trajectory.shape[0] - 1
        if n_steps < 1:
            raise ValueError("trajectory must have at least 2 rows")

        initial = CoherenceState.from_vector(trajectory[0])
        # Reconstruct inputs as zeros (we're analyzing, not simulating)
        return self.analyze(
            initial,
            n_steps,
            inputs=np.zeros((n_steps, 2), dtype=np.float64),
            rng=None,
            bifurcation_threshold=bifurcation_threshold,
        )
