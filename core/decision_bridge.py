"""Decision Bridge — unified analytical convergence point.

Connects the NeoSynaptex engine output to the full analytical stack:
coherence state-space, FDT γ-estimation, OEB control, hallucination
detection, resonance mapping, and gradient ontology diagnosis.

This is the architectural center where all modules converge into a
single, enriched decision object.

Architecture::

    neosynaptex.observe()
           │
           ▼
    ┌─────────────────────────────┐
    │     Decision Bridge         │
    │                             │
    │  ┌───────┐  ┌───────────┐  │
    │  │ State  │  │ Resonance │  │
    │  │ Space  │──│   Map     │  │
    │  └───┬───┘  └─────┬─────┘  │
    │      │            │        │
    │  ┌───▼───┐  ┌─────▼─────┐  │
    │  │  FDT  │  │Hallucin.  │  │
    │  │  γ̂   │  │Benchmark  │  │
    │  └───┬───┘  └─────┬─────┘  │
    │      │            │        │
    │  ┌───▼────────────▼─────┐  │
    │  │    OEB Controller    │  │
    │  └──────────┬───────────┘  │
    │             │              │
    │  ┌──────────▼───────────┐  │
    │  │   INV-YV1 Diagnosis  │  │
    │  └──────────┬───────────┘  │
    └─────────────┼──────────────┘
                  ▼
         DecisionSnapshot
         (enriched state)

Design:
- Pure function: takes engine state arrays, returns enriched snapshot.
- No mutation of engine state.
- Lazy evaluation: each analysis runs only if data is sufficient.
- All thresholds from core.constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
    CoherenceStateSpaceParams,
)
from core.constants import (
    BIFURCATION_THRESHOLD,
    GAMMA_THRESHOLD_METASTABLE,
    INV_YV1_D_DELTA_V_MIN,
    INV_YV1_DELTA_V_MIN,
)

__all__ = [
    "DecisionSnapshot",
    "DecisionBridge",
]

FloatArray = NDArray[np.float64]

_MIN_HISTORY: Final[int] = 4  # minimum ticks before bridge activates


@dataclass(frozen=True)
class DecisionSnapshot:
    """Enriched analytical state — convergence of all modules.

    This is the output of the Decision Bridge: a single object
    that captures what the system knows about itself RIGHT NOW.
    """

    # ── Identity ────────────────────────────────────────────────────
    tick: int

    # ── From engine ─────────────────────────────────────────────────
    gamma_mean: float
    gamma_std: float
    spectral_radius: float
    phase: str

    # ── Coherence state-space projection ────────────────────────────
    projected_coherence: float  # S from state-space model
    projected_gamma: float  # γ from state-space model
    projected_e_obj: float  # objection energy level
    state_space_stable: bool

    # ── Resonance diagnostics ───────────────────────────────────────
    operating_regime: str  # frozen / critical / chaotic
    near_bifurcation: bool
    time_to_diagnosis: int

    # ── FDT γ quality ───────────────────────────────────────────────
    gamma_fdt_available: bool
    gamma_fdt_estimate: float  # NaN if not available
    gamma_fdt_uncertainty: float

    # ── Hallucination risk ──────────────────────────────────────────
    delta_s_trend: float  # mean ΔS over recent window (positive = healthy)
    hallucination_risk: str  # "low" / "moderate" / "high"

    # ── OEB status ──────────────────────────────────────────────────
    critic_gain: float
    energy_remaining_frac: float  # 0–1

    # ── INV-YV1 gradient ontology ───────────────────────────────────
    gradient_diagnosis: str  # living_gradient / static_capacitor / dead_equilibrium / transient
    alive_frac: float
    dynamic_frac: float

    # ── Unified verdict ─────────────────────────────────────────────
    system_health: str  # "OPTIMAL" / "DEGRADED" / "CRITICAL" / "DEAD"
    confidence: float  # 0–1: how much data the bridge had


class DecisionBridge:
    """Unified analytical convergence point.

    Usage::

        bridge = DecisionBridge()
        # After engine.observe() accumulates history:
        snapshot = bridge.evaluate(
            tick=state.t,
            gamma_mean=state.gamma_mean,
            gamma_std=state.gamma_std,
            spectral_radius=state.spectral_radius,
            phase=state.phase,
            phi_history=np.array([s.phi for s in engine.history()]),
            gamma_history=np.array([s.gamma_mean for s in engine.history()]),
        )
        print(snapshot.system_health, snapshot.gradient_diagnosis)
    """

    def __init__(
        self,
        state_space_params: CoherenceStateSpaceParams | None = None,
    ) -> None:
        self._model = CoherenceStateSpace(state_space_params)
        self._oeb_gain: float = 0.05  # initial critic gain
        self._oeb_energy: float = 1.0  # initial energy budget (normalized)
        self._prev_gamma: float = float("nan")

    def evaluate(
        self,
        tick: int,
        gamma_mean: float,
        gamma_std: float,
        spectral_radius: float,
        phase: str,
        phi_history: FloatArray,
        gamma_history: FloatArray,
    ) -> DecisionSnapshot:
        """Run full analytical pipeline on current engine state.

        Args:
            tick: current engine tick.
            gamma_mean: cross-domain γ mean from engine.
            gamma_std: cross-domain γ std.
            spectral_radius: Jacobian spectral radius.
            phase: engine phase label.
            phi_history: (T, D) array of recent phi vectors.
            gamma_history: (T,) array of recent γ means.

        Returns:
            DecisionSnapshot with all analyses.
        """
        n = phi_history.shape[0] if phi_history.ndim == 2 else 0
        confidence = min(1.0, n / 16.0)  # full confidence at 16 ticks

        # ── State-space projection ──────────────────────────────────
        s_proj = 0.5
        g_proj = gamma_mean if np.isfinite(gamma_mean) else 1.0
        e_proj = 0.0
        ss_stable = True

        if n >= _MIN_HISTORY:
            # Project engine γ into state-space coordinates
            s_proj = float(np.clip(1.0 - gamma_std, 0, 1))  # low std → high coherence
            e_proj = max(0.0, spectral_radius - 1.0)  # excess instability → objection
            state = CoherenceState(S=s_proj, gamma=g_proj, E_obj=e_proj, sigma2=gamma_std**2)
            report = self._model.stability(state)
            ss_stable = report.is_stable

        # ── Resonance ───────────────────────────────────────────────
        operating_regime = "critical"
        near_bif = False
        ttd = tick

        if n >= _MIN_HISTORY:
            from core.resonance_map import ResonanceAnalyzer

            analyzer = ResonanceAnalyzer(self._model)
            # Build mini-trajectory from projected states
            if phi_history.ndim == 2 and phi_history.shape[1] >= 2:
                mini_n = min(n, 30)
                recent_g = gamma_history[-mini_n:]
                # Create synthetic trajectory for resonance analysis
                traj = np.zeros((mini_n, 4), dtype=np.float64)
                traj[:, 0] = np.clip(1.0 - np.abs(recent_g - 1.0), 0, 1)  # S from γ
                traj[:, 1] = recent_g  # γ
                traj[:, 2] = np.maximum(0, np.abs(np.diff(recent_g, prepend=recent_g[0])))  # E
                traj[:, 3] = gamma_std**2  # σ²

                rmap = analyzer.analyze_trajectory(traj)
                operating_regime = rmap.dominant_regime
                near_bif = bool(rmap.spectral_radius_trajectory[-1] > BIFURCATION_THRESHOLD)
                ttd = rmap.time_to_diagnosis

        # ── FDT γ estimate ──────────────────────────────────────────
        gamma_fdt = float("nan")
        gamma_fdt_unc = float("nan")
        fdt_available = False

        if n >= 10 and np.isfinite(self._prev_gamma):
            from core.gamma_fdt_estimator import GammaFDTEstimator

            noise = gamma_history[:-1]
            response = gamma_history[1:]
            if len(noise) >= 8:
                try:
                    est = GammaFDTEstimator(dt=1.0, bootstrap_n=50, seed=tick)
                    perturbation = float(gamma_history[-1] - gamma_history[-2])
                    if abs(perturbation) > 1e-8:
                        result = est.estimate(noise, response, perturbation)
                        gamma_fdt = result.gamma_hat
                        gamma_fdt_unc = result.uncertainty
                        fdt_available = True
                except (ValueError, ZeroDivisionError):
                    pass

        self._prev_gamma = gamma_mean

        # ── ΔS trend (hallucination risk) ───────────────────────────
        delta_s_trend = 0.0
        halluc_risk = "low"

        if n >= 3:
            s_series = np.clip(1.0 - np.abs(gamma_history - 1.0), 0, 1)
            ds = np.diff(s_series)
            delta_s_trend = float(np.mean(ds[-min(10, len(ds)) :]))
            if delta_s_trend < -0.02:
                halluc_risk = "high"
            elif delta_s_trend < 0.0:
                halluc_risk = "moderate"

        # ── OEB (simple proportional update) ────────────────────────
        if halluc_risk == "high":
            self._oeb_gain = min(self._oeb_gain * 1.2, 1.0)
        elif halluc_risk == "low":
            self._oeb_gain = max(self._oeb_gain * 0.95, 0.01)
        self._oeb_energy = max(0.0, self._oeb_energy - self._oeb_gain * 0.01)

        # ── INV-YV1 ────────────────────────────────────────────────
        alive_frac = 0.0
        dynamic_frac = 0.0
        grad_diag = "unknown"

        if n >= _MIN_HISTORY and phi_history.ndim == 2:
            equilibrium = np.mean(phi_history, axis=0)
            dv = np.linalg.norm(phi_history - equilibrium, axis=1)
            alive_frac = float(np.mean(dv > INV_YV1_DELTA_V_MIN))
            ddv = np.abs(np.diff(dv))
            dynamic_frac = float(np.mean(ddv > INV_YV1_D_DELTA_V_MIN)) if len(ddv) > 0 else 0.0

            if alive_frac <= 0.5:
                grad_diag = "dead_equilibrium"
            elif dynamic_frac <= 0.5:
                grad_diag = "static_capacitor"
            elif alive_frac > 0.9 and dynamic_frac > 0.9:
                grad_diag = "living_gradient"
            else:
                grad_diag = "transient"

        # ── Unified verdict ─────────────────────────────────────────
        health = _compute_health(
            grad_diag,
            operating_regime,
            halluc_risk,
            ss_stable,
            gamma_mean,
        )

        return DecisionSnapshot(
            tick=tick,
            gamma_mean=gamma_mean,
            gamma_std=gamma_std,
            spectral_radius=spectral_radius,
            phase=phase,
            projected_coherence=s_proj,
            projected_gamma=g_proj,
            projected_e_obj=e_proj,
            state_space_stable=ss_stable,
            operating_regime=operating_regime,
            near_bifurcation=near_bif,
            time_to_diagnosis=ttd,
            gamma_fdt_available=fdt_available,
            gamma_fdt_estimate=gamma_fdt,
            gamma_fdt_uncertainty=gamma_fdt_unc,
            delta_s_trend=delta_s_trend,
            hallucination_risk=halluc_risk,
            critic_gain=self._oeb_gain,
            energy_remaining_frac=self._oeb_energy,
            gradient_diagnosis=grad_diag,
            alive_frac=alive_frac,
            dynamic_frac=dynamic_frac,
            system_health=health,
            confidence=confidence,
        )

    def reset(self) -> None:
        """Reset bridge state for new session."""
        self._oeb_gain = 0.05
        self._oeb_energy = 1.0
        self._prev_gamma = float("nan")


def _compute_health(
    grad_diag: str,
    regime: str,
    halluc_risk: str,
    stable: bool,
    gamma: float,
) -> str:
    """Compute unified system health from all diagnostic signals."""
    if grad_diag == "dead_equilibrium":
        return "DEAD"
    if grad_diag == "static_capacitor" or not stable:
        return "CRITICAL"
    if halluc_risk == "high" or regime == "chaotic":
        return "DEGRADED"
    if (
        regime == "critical"
        and halluc_risk == "low"
        and abs(gamma - 1.0) < GAMMA_THRESHOLD_METASTABLE
    ):
        return "OPTIMAL"
    return "DEGRADED"
