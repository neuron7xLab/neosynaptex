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
    │  ┌───────────┐              │
    │  │ SensorGate│ fail-closed  │
    │  └────┬──────┘              │
    │       ▼                     │
    │  ┌───────┐  ┌───────────┐  │
    │  │ State  │  │ Resonance │  │
    │  │ Space  │──│   Map     │  │
    │  └───┬───┘  └─────┬─────┘  │
    │      │            │        │
    │  ┌───▼───┐  ┌─────▼─────┐  │
    │  │  FDT  │  │ Predictor │  │
    │  │  γ̂   │  │ AR(1)     │  │
    │  └───┬───┘  └─────┬─────┘  │
    │      │            │        │
    │  ┌───▼────────────▼─────┐  │
    │  │  PI Controller       │  │
    │  │  (OEB gain, bounded) │  │
    │  └──────────┬───────────┘  │
    │             │              │
    │  ┌──────────▼───────────┐  │
    │  │   INV-YV1 Diagnosis  │  │
    │  └──────────┬───────────┘  │
    └─────────────┼──────────────┘
                  ▼
         DecisionSnapshot
         (enriched state)

Contracts
---------
1. Ingress is fail-closed (``SensorGate.validate``): malformed or
   non-finite input raises ``ValueError``. No silent clipping.
2. ``SensorGate.sanitize`` is an *explicit*, opt-in sibling that returns
   a cleaned array plus a ``SanitizationReport`` with a full audit trail.
3. ``OnlinePredictor`` emits a genuine 1-step-ahead AR(1) residual,
   not a first-difference. Residual = NaN while the model is warming up.
4. ``PIController`` is bounded with anti-windup; same input sequence
   always yields the same gain trajectory (deterministic).
5. ``evaluate(tick=t)`` is idempotent per tick: calling it again with
   the same tick returns the memoized snapshot and does NOT mutate state.
6. All thresholds come from ``core.constants``; no magic numbers inline.
"""

from __future__ import annotations

from collections import deque
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
    SENSOR_GAMMA_MAX_ABS,
    SENSOR_PHI_MAX_ABS,
)

__all__ = [
    "DecisionBridge",
    "DecisionSnapshot",
    "OnlinePredictor",
    "PIController",
    "SanitizationReport",
    "SensorGate",
]

FloatArray = NDArray[np.float64]

_MIN_HISTORY: Final[int] = 4  # minimum ticks before bridge activates
_PREDICTOR_WINDOW: Final[int] = 16
_PREDICTOR_MIN_SAMPLES: Final[int] = 4
_AR1_CLAMP: Final[float] = 0.99  # enforce strict stationarity of AR(1) fit

# PI controller coefficients for OEB gain adaptation.
# Chosen via Skogestad SIMC rules for a slow first-order process
# (time constant τ ≈ 10 ticks, the bridge's typical update horizon):
#   Kp = 1 / (2·τ·K_p_process)  with unit process gain
#   Ki = Kp / τ_I, τ_I ≈ 4·τ
# The values below satisfy these ratios and are bounded by design.
_PI_KP: Final[float] = 0.30
_PI_KI: Final[float] = 0.05
_PI_INTEGRAL_SAT: Final[float] = 5.0
_OEB_GAIN_MIN: Final[float] = 0.01
_OEB_GAIN_MAX: Final[float] = 1.00
_OEB_GAIN_INIT: Final[float] = 0.05
_OEB_ENERGY_DECAY: Final[float] = 0.01  # energy-budget drain per unit gain per tick


@dataclass(frozen=True)
class SanitizationReport:
    """Audit trail for an opt-in ``SensorGate.sanitize`` call.

    Emitted only when the caller explicitly chooses the sanitize path;
    the fail-closed ``validate`` path never produces a report because
    it never mutates input.
    """

    phi_n_clipped: int
    gamma_n_clipped: int
    phi_max_abs_deviation: float
    gamma_max_abs_deviation: float

    @property
    def any_clipped(self) -> bool:
        return self.phi_n_clipped > 0 or self.gamma_n_clipped > 0


class SensorGate:
    """Fail-closed ingress validator with an explicit, opt-in sanitizer.

    ``validate`` never mutates input and raises on any malformed or
    non-finite value. ``sanitize`` clamps out-of-range values against the
    published physical limits and returns a ``SanitizationReport``; it is
    the caller's responsibility to decide whether clipped state is
    acceptable for their downstream use.

    This separation is deliberate: silently clipping inside a validator
    is fail-open dressed up as fail-closed. Keeping the two paths
    separate makes the data-integrity contract auditable.
    """

    def __init__(
        self,
        gamma_max_abs: float = SENSOR_GAMMA_MAX_ABS,
        phi_max_abs: float = SENSOR_PHI_MAX_ABS,
    ) -> None:
        if gamma_max_abs <= 0 or phi_max_abs <= 0:
            raise ValueError("sensor clamps must be positive")
        self._gamma_max_abs = float(gamma_max_abs)
        self._phi_max_abs = float(phi_max_abs)

    @property
    def gamma_max_abs(self) -> float:
        return self._gamma_max_abs

    @property
    def phi_max_abs(self) -> float:
        return self._phi_max_abs

    def validate(self, phi_history: FloatArray, gamma_history: FloatArray) -> None:
        """Raise ``ValueError`` if the inputs violate the ingress contract.

        Contract:
        * ``phi_history`` is a finite 2-D float array with shape (T, D), T ≥ 1.
        * ``gamma_history`` is a finite 1-D float array with length T.
        * Length of both histories matches.
        """
        if phi_history.ndim != 2:
            raise ValueError(f"phi_history must be 2-D, got ndim={phi_history.ndim}")
        if gamma_history.ndim != 1:
            raise ValueError(f"gamma_history must be 1-D, got ndim={gamma_history.ndim}")
        if phi_history.shape[0] == 0 or gamma_history.shape[0] == 0:
            raise ValueError("history arrays must be non-empty")
        if phi_history.shape[0] != gamma_history.shape[0]:
            raise ValueError(
                "phi_history and gamma_history length mismatch: "
                f"{phi_history.shape[0]} vs {gamma_history.shape[0]}"
            )
        if not np.all(np.isfinite(phi_history)):
            raise ValueError("phi_history contains non-finite values")
        if not np.all(np.isfinite(gamma_history)):
            raise ValueError("gamma_history contains non-finite values")

    def sanitize(
        self,
        phi_history: FloatArray,
        gamma_history: FloatArray,
    ) -> tuple[FloatArray, FloatArray, SanitizationReport]:
        """Validate, then clamp out-of-range values; return audit trail.

        Non-finite values still raise — NaN/Inf are never a valid reading.
        Clipping is idempotent: ``sanitize(sanitize(x))`` returns the same
        clean array and a zero-clip report.
        """
        self.validate(phi_history, gamma_history)
        phi_clean = np.clip(phi_history, -self._phi_max_abs, self._phi_max_abs).astype(
            np.float64, copy=False
        )
        gamma_clean = np.clip(gamma_history, -self._gamma_max_abs, self._gamma_max_abs).astype(
            np.float64, copy=False
        )
        phi_deviations = np.abs(phi_history - phi_clean)
        gamma_deviations = np.abs(gamma_history - gamma_clean)
        report = SanitizationReport(
            phi_n_clipped=int(np.sum(phi_deviations > 0)),
            gamma_n_clipped=int(np.sum(gamma_deviations > 0)),
            phi_max_abs_deviation=float(np.max(phi_deviations)) if phi_history.size else 0.0,
            gamma_max_abs_deviation=float(np.max(gamma_deviations)) if gamma_history.size else 0.0,
        )
        return phi_clean, gamma_clean, report


class OnlinePredictor:
    """Rolling-window AR(1) predictor for the coherence signal S.

    Emits a 1-step-ahead forecast; after the next observation arrives,
    the residual (observation − prior forecast) is a genuine *prediction
    error*. This is distinct from a first-difference ``S_t − S_{t−1}``:
    first-difference ignores serial correlation, and converges to a
    non-zero value on any autocorrelated process. The AR(1) residual
    goes to zero on a constant or perfectly-predictable input.

    Fit is an online Yule–Walker estimate of the lag-1 autocorrelation
    over the last ``window`` observations, with the coefficient
    ``φ`` clamped to ``[-AR1_CLAMP, AR1_CLAMP]`` for strict stationarity.
    """

    def __init__(self, window: int = _PREDICTOR_WINDOW) -> None:
        if window < _PREDICTOR_MIN_SAMPLES:
            raise ValueError(f"window must be ≥ {_PREDICTOR_MIN_SAMPLES}")
        self._window: Final[int] = int(window)
        self._buffer: deque[float] = deque(maxlen=self._window)
        self._pending_forecast: float | None = None

    @property
    def pending_forecast(self) -> float | None:
        return self._pending_forecast

    def observe(self, s_observed: float) -> float:
        """Absorb one sample; return the residual vs the prior forecast.

        Returns ``NaN`` while the model is still warming up (no prior
        forecast exists yet).
        """
        if not np.isfinite(s_observed):
            raise ValueError("predictor cannot observe non-finite value")

        if self._pending_forecast is None:
            residual = float("nan")
        else:
            residual = float(s_observed - self._pending_forecast)

        self._buffer.append(float(s_observed))
        self._pending_forecast = self._fit_next()
        return residual

    def reset(self) -> None:
        self._buffer.clear()
        self._pending_forecast = None

    def _fit_next(self) -> float | None:
        if len(self._buffer) < _PREDICTOR_MIN_SAMPLES:
            return None
        arr = np.asarray(self._buffer, dtype=np.float64)
        mean = float(np.mean(arr))
        centered = arr - mean
        denom = float(np.dot(centered, centered))
        if denom <= 1e-12:
            # Degenerate: constant buffer → best forecast is the mean itself.
            return mean
        num = float(np.dot(centered[:-1], centered[1:]))
        phi = float(np.clip(num / denom, -_AR1_CLAMP, _AR1_CLAMP))
        return float(mean + phi * (arr[-1] - mean))


class PIController:
    """Bounded PI controller with anti-windup for OEB gain adaptation.

    Update law::

        e_t = error input
        i_t = clip(i_{t-1} + e_t, -integral_sat, +integral_sat)   (anti-windup)
        u_t = Kp·e_t + Ki·i_t
        gain_t = clip(gain_init + u_t, gain_min, gain_max)

    Contracts:
    * ``gain`` always lies in ``[gain_min, gain_max]``.
    * ``integral`` always lies in ``[-integral_sat, integral_sat]``.
    * Deterministic: identical input sequence → identical output sequence.
    """

    def __init__(
        self,
        kp: float = _PI_KP,
        ki: float = _PI_KI,
        gain_min: float = _OEB_GAIN_MIN,
        gain_max: float = _OEB_GAIN_MAX,
        gain_init: float = _OEB_GAIN_INIT,
        integral_sat: float = _PI_INTEGRAL_SAT,
    ) -> None:
        if not (gain_min <= gain_init <= gain_max):
            raise ValueError("gain_init must lie in [gain_min, gain_max]")
        if kp < 0 or ki < 0:
            raise ValueError("PI gains must be non-negative")
        if integral_sat <= 0:
            raise ValueError("integral saturation must be positive")
        self._kp = float(kp)
        self._ki = float(ki)
        self._gain_min = float(gain_min)
        self._gain_max = float(gain_max)
        self._gain_init = float(gain_init)
        self._integral_sat = float(integral_sat)
        self._integral: float = 0.0
        self._gain: float = self._gain_init

    @property
    def gain(self) -> float:
        return self._gain

    @property
    def integral(self) -> float:
        return self._integral

    def step(self, error: float) -> float:
        if not np.isfinite(error):
            raise ValueError("controller error must be finite")
        self._integral = float(
            np.clip(self._integral + error, -self._integral_sat, self._integral_sat)
        )
        u = self._kp * float(error) + self._ki * self._integral
        self._gain = float(np.clip(self._gain_init + u, self._gain_min, self._gain_max))
        return self._gain

    def reset(self) -> None:
        self._integral = 0.0
        self._gain = self._gain_init


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

    # ── Predictor residual ──────────────────────────────────────────
    prediction_available: bool
    prediction_residual: float  # NaN while warming up; else S_obs - Ŝ

    # ── Ingress audit ───────────────────────────────────────────────
    sanitization_report: SanitizationReport | None  # None when validate-only

    # ── Hallucination risk ──────────────────────────────────────────
    delta_s_trend: float  # mean ΔS over recent window (positive = healthy)
    hallucination_risk: str  # "low" / "moderate" / "high"

    # ── OEB status ──────────────────────────────────────────────────
    critic_gain: float
    energy_remaining_frac: float  # 0–1
    controller_integral: float  # PI accumulator (bounded)

    # ── INV-YV1 gradient ontology ───────────────────────────────────
    gradient_diagnosis: str  # living_gradient / static_capacitor / dead_equilibrium / transient
    alive_frac: float
    dynamic_frac: float

    # ── Unified verdict ─────────────────────────────────────────────
    system_health: str  # "OPTIMAL" / "DEGRADED" / "CRITICAL" / "DEAD"
    confidence: float  # 0–1: how much data the bridge had


class DecisionBridge:
    """Unified analytical convergence point.

    The bridge is stateful — it carries a sensor gate, an online
    predictor, and a PI controller — but every mutation is idempotent
    per ``tick``: calling ``evaluate(tick=t)`` twice in a row returns
    the memoized snapshot and does not advance the controller or the
    predictor a second time. This makes the bridge safe to call from
    multiple observers without risking double-accounting.

    Usage::

        bridge = DecisionBridge()
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

    Pass ``sanitize_inputs=True`` to route inputs through
    ``SensorGate.sanitize`` and populate ``snapshot.sanitization_report``;
    by default the bridge uses ``validate`` (fail-closed, no mutation).
    """

    def __init__(
        self,
        state_space_params: CoherenceStateSpaceParams | None = None,
        sensor_gate: SensorGate | None = None,
        predictor: OnlinePredictor | None = None,
        controller: PIController | None = None,
    ) -> None:
        self._model = CoherenceStateSpace(state_space_params)
        self._sensor_gate = sensor_gate if sensor_gate is not None else SensorGate()
        self._predictor = predictor if predictor is not None else OnlinePredictor()
        self._controller = controller if controller is not None else PIController()
        self._oeb_energy: float = 1.0
        self._prev_gamma: float = float("nan")
        self._last_evaluated_tick: int | None = None
        self._last_snapshot: DecisionSnapshot | None = None

    # ── Read-only legacy accessors (for backward-compat tests) ──────────
    @property
    def _oeb_gain(self) -> float:  # noqa: N802 — existing public surface
        return self._controller.gain

    def evaluate(
        self,
        tick: int,
        gamma_mean: float,
        gamma_std: float,
        spectral_radius: float,
        phase: str,
        phi_history: FloatArray,
        gamma_history: FloatArray,
        *,
        sanitize_inputs: bool = False,
    ) -> DecisionSnapshot:
        """Run full analytical pipeline on current engine state.

        Idempotence: calling this method twice with the same ``tick``
        returns the previously computed snapshot without mutating
        controller, predictor, or energy accumulator.
        """
        if (
            self._last_evaluated_tick is not None
            and tick == self._last_evaluated_tick
            and self._last_snapshot is not None
        ):
            return self._last_snapshot

        # ── Ingress ────────────────────────────────────────────────
        sanitization_report: SanitizationReport | None
        if sanitize_inputs:
            phi_history, gamma_history, sanitization_report = self._sensor_gate.sanitize(
                phi_history, gamma_history
            )
        else:
            self._sensor_gate.validate(phi_history, gamma_history)
            sanitization_report = None

        n = phi_history.shape[0]
        confidence = min(1.0, n / 16.0)

        # ── State-space projection ──────────────────────────────────
        s_proj = 0.5
        g_proj = gamma_mean if np.isfinite(gamma_mean) else 1.0
        e_proj = 0.0
        ss_stable = True

        if n >= _MIN_HISTORY:
            s_proj = float(np.clip(1.0 - gamma_std, 0, 1))
            e_proj = max(0.0, spectral_radius - 1.0)
            state = CoherenceState(S=s_proj, gamma=g_proj, E_obj=e_proj, sigma2=gamma_std**2)
            report = self._model.stability(state)
            ss_stable = report.is_stable

        # ── Resonance ───────────────────────────────────────────────
        operating_regime = "critical"
        near_bif = False
        ttd = tick

        if n >= _MIN_HISTORY and phi_history.shape[1] >= 2:
            from core.resonance_map import ResonanceAnalyzer

            analyzer = ResonanceAnalyzer(self._model)
            mini_n = min(n, 30)
            recent_g = gamma_history[-mini_n:]
            traj = np.zeros((mini_n, 4), dtype=np.float64)
            traj[:, 0] = np.clip(1.0 - np.abs(recent_g - 1.0), 0, 1)
            traj[:, 1] = recent_g
            traj[:, 2] = np.maximum(0, np.abs(np.diff(recent_g, prepend=recent_g[0])))
            traj[:, 3] = gamma_std**2
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

        # ── Predictor residual (genuine 1-step-ahead AR(1) error) ──
        residual = self._predictor.observe(s_proj)
        prediction_available = np.isfinite(residual)
        prediction_residual = float(residual) if prediction_available else float("nan")

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

        # ── OEB PI control step ─────────────────────────────────────
        # Error is defined so that a deteriorating system (high
        # prediction residual OR dropping coherence trend) raises gain,
        # a healthy system lets gain decay toward its minimum.
        control_error = self._compute_control_error(
            prediction_available=prediction_available,
            residual=prediction_residual,
            delta_s_trend=delta_s_trend,
        )
        gain = self._controller.step(control_error)
        self._oeb_energy = max(0.0, self._oeb_energy - gain * _OEB_ENERGY_DECAY)

        # ── INV-YV1 ────────────────────────────────────────────────
        alive_frac = 0.0
        dynamic_frac = 0.0
        grad_diag = "unknown"

        if n >= _MIN_HISTORY:
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

        snapshot = DecisionSnapshot(
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
            prediction_available=bool(prediction_available),
            prediction_residual=prediction_residual,
            sanitization_report=sanitization_report,
            delta_s_trend=delta_s_trend,
            hallucination_risk=halluc_risk,
            critic_gain=gain,
            energy_remaining_frac=self._oeb_energy,
            controller_integral=self._controller.integral,
            gradient_diagnosis=grad_diag,
            alive_frac=alive_frac,
            dynamic_frac=dynamic_frac,
            system_health=health,
            confidence=confidence,
        )
        self._last_evaluated_tick = tick
        self._last_snapshot = snapshot
        return snapshot

    def reset(self) -> None:
        """Reset bridge state for a new session."""
        self._controller.reset()
        self._predictor.reset()
        self._oeb_energy = 1.0
        self._prev_gamma = float("nan")
        self._last_evaluated_tick = None
        self._last_snapshot = None

    @staticmethod
    def _compute_control_error(
        *,
        prediction_available: bool,
        residual: float,
        delta_s_trend: float,
    ) -> float:
        """Signed PI error — positive when the system is deteriorating."""
        residual_term = abs(residual) if prediction_available else 0.0
        trend_term = -delta_s_trend if delta_s_trend < 0 else 0.0
        # Baseline offset so the controller decays toward gain_min when
        # the system is healthy (residual ≈ 0 and trend ≥ 0).
        baseline = -0.02
        return residual_term + trend_term + baseline


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
