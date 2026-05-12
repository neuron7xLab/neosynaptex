"""Regime monitoring and action/rest gating for online adaptation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from scipy import signal

from bnsyn.regime_constants import DEFAULT_WELCH_NPERSEG, EPSILON, MIN_SERIES_LEN, SIGMOID_CLIP_HIGH, SIGMOID_CLIP_LOW
from bnsyn.regime_ledger import RegimeRunRecord, append_run_record_jsonl, build_run_record
from bnsyn.regime_validation import RegimeControllerConfigModel, RegimeStepInputModel

__all__ = [
    "RegimeMemory",
    "RegimeGate",
    "RegimeStepDiagnostics",
    "RegimeController",
    "compute_gamma",
    "estimate_hurst_from_psd",
    "adaptive_update",
    "ema_decay",
    "RegimeRunRecord",
    "build_run_record",
    "append_run_record_jsonl",
]


def _linear_slope(x_values: np.ndarray, y_values: np.ndarray) -> float:
    x_mean = float(np.mean(x_values))
    y_mean = float(np.mean(y_values))
    denom = float(np.sum((x_values - x_mean) ** 2))
    if denom <= EPSILON:
        return 0.0
    return float(np.sum((x_values - x_mean) * (y_values - y_mean)) / denom)


def estimate_hurst_from_psd(freqs: np.ndarray, psd: np.ndarray) -> float:
    freqs_arr = np.asarray(freqs, dtype=np.float64)
    psd_arr = np.asarray(psd, dtype=np.float64)
    mask = (freqs_arr > 0.0) & np.isfinite(freqs_arr) & np.isfinite(psd_arr) & (psd_arr > 0.0)
    if int(np.sum(mask)) < 4:
        return 0.5
    beta = -_linear_slope(np.log(freqs_arr[mask]), np.log(psd_arr[mask]))
    return float(np.clip(0.5 * (beta - 1.0), 0.0, 1.0))


def compute_gamma(activations: np.ndarray, welch_nperseg: int = DEFAULT_WELCH_NPERSEG) -> float:
    """Estimate gamma proxy from activation signal via Welch PSD.

    Parameters
    ----------
    activations : np.ndarray
        Activation vector or tensor (flattened internally).
    welch_nperseg : int
        Segment length for Welch PSD.

    Returns
    -------
    float
        Gamma proxy value or NaN for invalid/short input.
    """
    activations_arr = np.asarray(activations, dtype=np.float64).reshape(-1)
    if activations_arr.size < MIN_SERIES_LEN or not np.all(np.isfinite(activations_arr)):
        return float("nan")
    freqs, psd = signal.welch(activations_arr, nperseg=min(welch_nperseg, activations_arr.size))
    return float(2.0 * estimate_hurst_from_psd(freqs, psd) + 1.0)


def _sigmoid(x_value: float) -> float:
    x_clip = float(np.clip(x_value, SIGMOID_CLIP_LOW, SIGMOID_CLIP_HIGH))
    return float(1.0 / (1.0 + np.exp(-x_clip)))


@dataclass(slots=True)
class RegimeMemory:
    maxlen: int = 256
    _v_history: deque[float] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.maxlen < 2:
            raise ValueError("maxlen must be >= 2")
        self._v_history = deque(self._v_history, maxlen=self.maxlen)

    def push(self, value: float) -> None:
        if not np.isfinite(value):
            raise ValueError("value must be finite")
        self._v_history.append(float(value))

    @property
    def prev(self) -> float:
        return float(self._v_history[-1]) if self._v_history else 0.0

    def as_array(self) -> np.ndarray:
        return np.asarray(list(self._v_history), dtype=np.float64)


class GateProtocol:
    def gate(self, gamma: float, entropy: float) -> float:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass(slots=True)
class RegimeGate(GateProtocol):
    gamma_target: float = 1.0
    entropy_threshold: float = 0.3
    memory: RegimeMemory = field(default_factory=RegimeMemory)

    def gate(self, gamma: float, entropy: float) -> float:
        if not np.isfinite(gamma):
            raise ValueError("gamma must be finite")
        entropy_clipped = float(np.clip(entropy, 0.0, 1.0))
        entropy_factor = 0.0 if entropy_clipped >= self.entropy_threshold else (1.0 - entropy_clipped)
        v_now = float((gamma - self.gamma_target) * entropy_factor)
        out = _sigmoid(v_now - self.memory.prev)
        self.memory.push(v_now)
        return out


def ema_decay(weights: np.ndarray, alpha: float = 0.01) -> np.ndarray:
    weights_arr = np.asarray(weights, dtype=np.float64)
    return (1.0 - float(np.clip(alpha, 0.0, 1.0))) * weights_arr


def adaptive_update(weights: np.ndarray, grad: np.ndarray, gate_signal: float, learning_rate: float, rest_threshold: float = 0.1, ema_alpha: float = 0.01) -> np.ndarray:
    if not np.isfinite(gate_signal):
        raise ValueError("gate_signal must be finite")
    if learning_rate < 0.0:
        raise ValueError("learning_rate must be >= 0")
    weights_arr = np.asarray(weights, dtype=np.float64).copy()
    grad_arr = np.asarray(grad, dtype=np.float64).copy()
    if not np.all(np.isfinite(weights_arr)) or not np.all(np.isfinite(grad_arr)):
        raise ValueError("weights and grad must be finite")
    if weights_arr.shape != grad_arr.shape:
        raise ValueError("weights and grad must have identical shape")
    updated = weights_arr + learning_rate * grad_arr * float(gate_signal)
    if not np.all(np.isfinite(updated)):
        raise ValueError("adaptive update produced non-finite values")
    return ema_decay(updated, alpha=ema_alpha) if gate_signal < rest_threshold else updated


@dataclass(slots=True)
class RegimeStepDiagnostics:
    gamma: float
    entropy: float
    velocity: float
    gate_signal: float
    rest_phase: bool
    gamma_fallback_used: bool


@dataclass(slots=True)
class RegimeController:
    """Online regime controller orchestrating monitor-gate-update flow.

    Parameters
    ----------
    gate : RegimeGate
        Internal gate instance.
    learning_rate : float
        Non-negative update scale.
    rest_threshold : float
        Threshold below which rest-phase decay is applied.
    ema_alpha : float
        Decay factor for rest-phase update.
    grad_clip_abs : float
        Absolute gradient clipping bound.
    welch_nperseg : int
        PSD window length for gamma proxy.
    """
    gate: RegimeGate = field(default_factory=RegimeGate)
    learning_rate: float = 1e-3
    rest_threshold: float = 0.1
    ema_alpha: float = 0.01
    grad_clip_abs: float = 1e6
    welch_nperseg: int = DEFAULT_WELCH_NPERSEG

    def __post_init__(self) -> None:
        RegimeControllerConfigModel(
            learning_rate=self.learning_rate,
            rest_threshold=self.rest_threshold,
            ema_alpha=self.ema_alpha,
            grad_clip_abs=self.grad_clip_abs,
            welch_nperseg=self.welch_nperseg,
        )

    def step(self, weights: np.ndarray, grad: np.ndarray, activations: np.ndarray, entropy: float) -> tuple[np.ndarray, RegimeStepDiagnostics]:
        """Execute one control step.

        Parameters
        ----------
        weights : np.ndarray
            Current parameter vector/tensor.
        grad : np.ndarray
            Gradient estimate with same shape as `weights`.
        activations : np.ndarray
            Activation trace used for gamma proxy estimation.
        entropy : float
            Entropy signal, clipped to [0, 1] for diagnostics.

        Returns
        -------
        tuple[np.ndarray, RegimeStepDiagnostics]
            Updated weights and step diagnostics.

        Raises
        ------
        ValueError
            If numeric contracts are violated downstream.
        """
        RegimeStepInputModel(entropy=entropy)
        gamma = compute_gamma(activations, welch_nperseg=self.welch_nperseg)
        fallback = not np.isfinite(gamma)
        gamma_value = self.gate.gamma_target if fallback else float(gamma)
        gate_signal = self.gate.gate(gamma=gamma_value, entropy=entropy)
        grad_safe = np.clip(np.asarray(grad, dtype=np.float64), -self.grad_clip_abs, self.grad_clip_abs)
        updated = adaptive_update(weights, grad_safe, gate_signal, self.learning_rate, self.rest_threshold, self.ema_alpha)
        diagnostics = RegimeStepDiagnostics(
            gamma=gamma_value,
            entropy=float(np.clip(entropy, 0.0, 1.0)),
            velocity=float(self.gate.memory.prev),
            gate_signal=float(gate_signal),
            rest_phase=bool(gate_signal < self.rest_threshold),
            gamma_fallback_used=fallback,
        )
        return updated, diagnostics
