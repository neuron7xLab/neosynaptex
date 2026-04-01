from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from mlsdm.protocols.neuro_signals import (
    ActionGatingSignal,
    RewardPredictionErrorSignal,
    StabilityMetrics,
)
from mlsdm.utils.math_constants import safe_norm

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory


class RegimeState(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    DEFENSIVE = "defensive"


@dataclass
class RegimeDecision:
    state: RegimeState
    inhibition_gain: float
    exploration_rate: float
    tau_scale: float
    risk: float
    flips: int


@dataclass
class PredictionErrorMetrics:
    delta: float
    ema_delta: float
    bias: float
    adjusted_prediction: float
    residual_error: float


@dataclass
class NeuroAIStepMetrics:
    regime: RegimeDecision | None
    prediction_error: PredictionErrorMetrics | None
    oscillation_score: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class RegimeTuning:
    """
    Tuning parameters for regime dynamics and update scaling.

    Values are bounded to preserve legacy behavior: NORMAL tracks the previous
    dynamics, CAUTION increases inhibition and slightly shortens τ, DEFENSIVE
    applies the strongest inhibition with aggressive τ shortening.
    """

    min_update_scale: float = 0.2
    max_update_scale: float = 2.0
    normal_exploration_base: float = 0.25
    normal_inhibition_slope: float = 0.1
    normal_tau_scale: float = 1.0
    caution_inhibition_base: float = 1.15
    caution_inhibition_slope: float = 0.35
    caution_exploration_base: float = 0.22
    caution_exploration_min: float = 0.12
    caution_tau_min: float = 0.75
    caution_tau_slope: float = 0.25
    defensive_inhibition_base: float = 1.35
    defensive_inhibition_slope: float = 0.45
    defensive_exploration_base: float = 0.18
    defensive_exploration_min: float = 0.08
    defensive_tau_min: float = 0.6
    defensive_tau_slope: float = 0.4


_TUNING = RegimeTuning()


class PredictionErrorAdapter:
    """
    Bounded prediction-error learner.

    Learning is driven solely by prediction error (observed - predicted) with:
    - clipping of Δ to avoid instability
    - bounded bias update to keep gains in a safe range
    - EMA tracking for smooth observability
    """

    def __init__(
        self,
        learning_rate: float = 0.25,
        clip_value: float = 1.0,
        max_bias: float = 0.75,
        ema_alpha: float = 0.2,
    ) -> None:
        if not 0 < learning_rate <= 1:
            raise ValueError("learning_rate must be in (0, 1].")
        if clip_value <= 0:
            raise ValueError("clip_value must be positive.")
        if max_bias <= 0:
            raise ValueError("max_bias must be positive.")
        if not 0 < ema_alpha <= 1:
            raise ValueError("ema_alpha must be in (0, 1].")

        self.learning_rate = float(learning_rate)
        self.clip_value = float(clip_value)
        self.max_bias = float(max_bias)
        self.ema_alpha = float(ema_alpha)
        self.bias = 0.0
        self.ema_delta = 0.0

    def _to_scalar(self, value: float | np.ndarray) -> float:
        """Convert predictions/observations to a scalar using mean aggregation.

        Mean is used instead of max/sum to dampen outlier noise and keep the
        prediction-error signal stable across vector-valued inputs.
        """
        if isinstance(value, np.ndarray):
            return float(np.mean(value))
        return float(value)

    def update(self, predicted: float | np.ndarray, observed: float | np.ndarray) -> PredictionErrorMetrics:
        pred = self._to_scalar(predicted)
        obs = self._to_scalar(observed)
        delta = _clamp(obs - pred, -self.clip_value, self.clip_value)
        self.ema_delta = (1 - self.ema_alpha) * self.ema_delta + self.ema_alpha * delta
        self.bias = _clamp(self.bias + self.learning_rate * delta, -self.max_bias, self.max_bias)
        adjusted_prediction = pred + self.bias
        residual = obs - adjusted_prediction
        return PredictionErrorMetrics(
            delta=delta,
            ema_delta=self.ema_delta,
            bias=self.bias,
            adjusted_prediction=adjusted_prediction,
            residual_error=residual,
        )


class RegimeController:
    """
    Risk-aware regime controller with hysteresis and cooldown.

    Risk increases tighten inhibition gain, reduce exploration, and shorten time
    constants (tau_scale). Hysteresis and cooldown prevent flip-flop behavior.
    """

    def __init__(
        self,
        caution_threshold: float = 0.55,
        defensive_threshold: float = 0.8,
        hysteresis: float = 0.08,
        cooldown: int = 2,
        enable: bool = True,
    ) -> None:
        if not 0 <= caution_threshold < defensive_threshold <= 1:
            raise ValueError(
                "caution_threshold must be >=0 and < defensive_threshold, which must be <=1."
            )
        if hysteresis < 0:
            raise ValueError("hysteresis must be non-negative.")
        if cooldown < 0:
            raise ValueError("cooldown must be non-negative.")

        self.caution_threshold = float(caution_threshold)
        self.defensive_threshold = float(defensive_threshold)
        self.hysteresis = float(hysteresis)
        self.cooldown = int(cooldown)
        self.enable = enable
        self.state = RegimeState.NORMAL
        self._cooldown_remaining = 0
        self._flips = 0

    def _maybe_transition(self, risk: float) -> RegimeState:
        if not self.enable:
            return self.state

        risk_clamped = _clamp(risk, 0.0, 1.0)
        target = self.state

        upper_caution = self.caution_threshold + (self.hysteresis if self.state == RegimeState.CAUTION else 0.0)
        upper_defensive = self.defensive_threshold + (self.hysteresis if self.state == RegimeState.DEFENSIVE else 0.0)
        lower_caution = self.caution_threshold - self.hysteresis

        if risk_clamped >= upper_defensive:
            target = RegimeState.DEFENSIVE
        elif risk_clamped >= upper_caution:
            target = RegimeState.CAUTION
        elif risk_clamped <= lower_caution:
            target = RegimeState.NORMAL

        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            if target != self.state:
                return self.state

        if target != self.state:
            self._flips += 1
            self._cooldown_remaining = self.cooldown
            self.state = target

        return self.state

    def step(self, risk: float) -> RegimeDecision:
        state = self._maybe_transition(risk)
        risk_clamped = _clamp(risk, 0.0, 1.0)

        if state == RegimeState.NORMAL:
            inhibition_gain = 1.0 + _TUNING.normal_inhibition_slope * risk_clamped
            exploration_rate = _TUNING.normal_exploration_base - 0.05 * risk_clamped
            tau_scale = _TUNING.normal_tau_scale
        elif state == RegimeState.CAUTION:
            inhibition_gain = _TUNING.caution_inhibition_base + _TUNING.caution_inhibition_slope * risk_clamped
            exploration_rate = max(
                _TUNING.caution_exploration_min,
                _TUNING.caution_exploration_base - 0.12 * risk_clamped,
            )
            tau_scale = max(_TUNING.caution_tau_min, 1.0 - _TUNING.caution_tau_slope * risk_clamped)
        else:
            inhibition_gain = _TUNING.defensive_inhibition_base + _TUNING.defensive_inhibition_slope * risk_clamped
            exploration_rate = max(
                _TUNING.defensive_exploration_min,
                _TUNING.defensive_exploration_base - 0.15 * risk_clamped,
            )
            tau_scale = max(_TUNING.defensive_tau_min, 1.0 - _TUNING.defensive_tau_slope * risk_clamped)

        return RegimeDecision(
            state=state,
            inhibition_gain=float(inhibition_gain),
            exploration_rate=float(exploration_rate),
            tau_scale=float(tau_scale),
            risk=risk_clamped,
            flips=self._flips,
        )


class SynapticMemoryAdapter:
    """
    Adapter for MultiLevelSynapticMemory that preserves legacy behavior by default.

    - When adaptation is disabled, update() delegates directly to the underlying
      memory with no parameter changes.
    - When enabled, prediction-error deltas modulate the update magnitude (bounded
      by max_bias) and risk signals modulate inhibition and time constants via
      the RegimeController.
    """

    def __init__(
        self,
        memory: MultiLevelSynapticMemory,
        *,
        enable_adaptation: bool = False,
        enable_regime_switching: bool = False,
        predictor: PredictionErrorAdapter | None = None,
        regime_controller: RegimeController | None = None,
    ) -> None:
        self.memory = memory
        self.enable_adaptation = enable_adaptation
        self.enable_regime_switching = enable_regime_switching
        self.predictor = predictor or PredictionErrorAdapter()
        self.regime_controller = regime_controller or RegimeController()

    def _scaled_event(
        self,
        event: np.ndarray,
        pe_metrics: PredictionErrorMetrics | None,
        regime: RegimeDecision | None,
    ) -> np.ndarray:
        scaled = event.astype(np.float32, copy=True)
        if pe_metrics is not None:
            scale = _clamp(
                1.0 + pe_metrics.bias,
                _TUNING.min_update_scale,
                _TUNING.max_update_scale,
            )
            scaled *= scale
        if regime is not None:
            scaled /= regime.inhibition_gain
        return scaled

    def _oscillation_score(self, traces: Iterable[np.ndarray]) -> float:
        """Compute oscillation proxy as the std-dev of L1/L2/L3 norms."""
        norms = [safe_norm(trace) for trace in traces]
        return float(np.std(norms))

    def update(
        self,
        event: np.ndarray,
        *,
        predicted: float | np.ndarray | None = None,
        observed: float | np.ndarray | None = None,
        risk: float | None = None,
        correlation_id: str | None = None,
    ) -> NeuroAIStepMetrics:
        pe_metrics: PredictionErrorMetrics | None = None
        if self.enable_adaptation and predicted is not None and observed is not None:
            pe_metrics = self.predictor.update(predicted, observed)

        regime: RegimeDecision | None = None
        if self.enable_regime_switching:
            regime = self.regime_controller.step(risk or 0.0)

        scaled_event = self._scaled_event(event, pe_metrics, regime)
        self.memory.update(scaled_event, correlation_id=correlation_id)

        l1, l2, l3 = self.memory.state()
        oscillation = self._oscillation_score((l1, l2, l3))
        return NeuroAIStepMetrics(regime=regime, prediction_error=pe_metrics, oscillation_score=oscillation)

    def get_state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.memory.state()


@dataclass(frozen=True)
class NeuroAIContractAdapter:
    """Adapter for exporting NeuroAI signals via contract models."""

    @staticmethod
    def reward_prediction_error_signal(metrics: PredictionErrorMetrics) -> RewardPredictionErrorSignal:
        delta = float(metrics.delta)
        return RewardPredictionErrorSignal(
            delta=[delta],
            abs_delta=abs(delta),
            clipped_delta=[delta],
            components=[abs(delta)],
        )

    @staticmethod
    def action_gating_signal(decision: RegimeDecision) -> ActionGatingSignal:
        return ActionGatingSignal(
            allow=True,
            reason="regime_controller",
            mode=decision.state.value,
            metadata={"risk": decision.risk, "flips": decision.flips},
        )

    @staticmethod
    def stability_metrics(step_metrics: NeuroAIStepMetrics) -> StabilityMetrics:
        oscillation = step_metrics.oscillation_score
        flips = step_metrics.regime.flips if step_metrics.regime else 0
        return StabilityMetrics(
            max_abs_delta=0.0,
            windowed_max_abs_delta=0.0,
            oscillation_index=oscillation,
            sign_flip_rate=0.0,
            regime_flip_rate=0.0,
            convergence_time=-1.0,
            instability_events_count=flips,
            time_to_kill_switch=None,
            recovered=False,
        )
