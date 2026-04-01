"""Discriminant — trajectory-aware pressure classification with calibrated uncertainty.

# IMPLEMENTED TRUTH: LogisticRegression + IsotonicRegression calibration pipeline.
# APPROXIMATION: linear classifier on handcrafted trajectory features.
# CALIBRATION: synthetic labels only, not real operational data.

Decision semantics:
  High uncertainty => OPERATIONAL (conservative default)
  EXISTENTIAL requires: calibrated p > threshold AND uncertainty acceptable
    AND hard irreversible-collapse guard OR overwhelming trajectory evidence
  Hysteresis: min_consecutive_existential steps before TRANSFORMATION

Read-only: does not modify system state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from .viability import ViabilityKernel

if TYPE_CHECKING:
    from .types import NormSpace

__all__ = [
    "CalibrationResult",
    "Discriminant",
    "DiscriminantResult",
    "PressureKind",
    "SystemMode",
    "TrajectoryDiscriminant",
]


class PressureKind(Enum):
    OPERATIONAL = "operational"
    EXISTENTIAL = "existential"


class SystemMode(Enum):
    IDLE = "idle"
    RECOVERY = "recovery"
    ADAPTATION = "adaptation"
    TRANSFORMATION = "transformation"


@dataclass(frozen=True)
class CalibrationResult:
    """# CALIBRATION: synthetic labels, not real operational data."""

    ece: float
    brier: float
    accuracy: float
    threshold: float
    noise_fpr: float  # false positive rate on operational data
    collapse_recall: float  # recall on existential data
    n_synthetic: int
    ece_method: str = "isotonic"
    label: str = "synthetic_calibration"


@dataclass(frozen=True)
class DiscriminantResult:
    """Structured discriminant output with full evidence trail."""

    pressure: PressureKind
    probability_existential: float
    uncertainty: float
    hard_guard_triggered: bool
    consecutive_existential: int
    hysteresis_blocked: bool
    explanation: str


class TrajectoryDiscriminant:
    """Trajectory-aware classifier with isotonic calibration + uncertainty gate.

    # IMPLEMENTED TRUTH: LogisticRegression + IsotonicRegression pipeline.
    # APPROXIMATION: linear classifier on 5 handcrafted features.
    # CALIBRATION: synthetic labels only, not real operational data.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        uncertainty_threshold: float = 0.4,
    ) -> None:
        self._w = np.array([2.0, 1.5, 3.0, -1.0, 0.5])
        self._b = -3.0
        self._mu = np.zeros(5)
        self._std = np.ones(5)
        self._scorer: object | None = None
        self._isotonic: object | None = None
        self.threshold = threshold
        self.uncertainty_threshold = uncertainty_threshold

    def classify(
        self,
        phi: float,
        phi_trend: float,
        failure_density: float,
        coherence: float,
        steps_in_bad_phase: int,
    ) -> tuple[PressureKind, float, float]:
        """Returns (kind, probability, uncertainty)."""
        z = np.array([phi, phi_trend, failure_density, coherence,
                       float(steps_in_bad_phase) / 100.0])

        if self._scorer is not None and self._isotonic is not None:
            z_2d = z.reshape(1, -1)
            p_raw = float(self._scorer.predict_proba(z_2d)[0, 1])
            score = float(np.clip(self._isotonic.predict([p_raw])[0], 0, 1))
        else:
            z_norm = (z - self._mu) / self._std
            logit = float(self._w @ z_norm + self._b)
            score = 1.0 / (1.0 + np.exp(-np.clip(logit, -20, 20)))

        uncertainty = 4.0 * score * (1.0 - score)

        if uncertainty > self.uncertainty_threshold:
            return PressureKind.OPERATIONAL, score, uncertainty

        if score > self.threshold:
            return PressureKind.EXISTENTIAL, score, uncertainty
        return PressureKind.OPERATIONAL, score, uncertainty

    @staticmethod
    def _to_z(d: dict[str, float]) -> np.ndarray:
        return np.array([
            d.get("phi", 0), d.get("phi_trend", 0),
            d.get("failure_density", 0), d.get("coherence", 0.5),
            d.get("steps_in_bad", 0) / 100.0,
        ])

    @staticmethod
    def _compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n = len(probs)
        for i in range(n_bins):
            mask = (probs >= bin_edges[i]) & (probs < bin_edges[i + 1])
            if i == n_bins - 1:
                mask = mask | (probs == bin_edges[i + 1])
            if mask.sum() == 0:
                continue
            ece += (mask.sum() / n) * abs(float(probs[mask].mean()) - float(labels[mask].mean()))
        return ece

    @staticmethod
    def _compute_brier(probs: np.ndarray, labels: np.ndarray) -> float:
        return float(np.mean((probs - labels) ** 2))

    def calibrate(
        self,
        operational: list[dict[str, float]],
        existential: list[dict[str, float]],
    ) -> CalibrationResult:
        """Two-stage calibration: LogisticRegression + IsotonicRegression.

        # IMPLEMENTED TRUTH: isotonic post-hoc calibration.
        # CALIBRATION: synthetic labels only, not real operational data.
        """
        from sklearn.isotonic import IsotonicRegression
        from sklearn.linear_model import LogisticRegression

        X_op = np.array([self._to_z(d) for d in operational])
        X_ex = np.array([self._to_z(d) for d in existential])
        X = np.vstack([X_op, X_ex])
        y = np.concatenate([np.zeros(len(X_op)), np.ones(len(X_ex))])

        rng = np.random.default_rng(42)
        idx = rng.permutation(len(X))
        split = int(len(X) * 0.8)
        train_idx, val_idx = idx[:split], idx[split:]
        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]

        scorer = LogisticRegression(max_iter=1000, random_state=42)
        scorer.fit(X_train, y_train)
        p_val_raw = scorer.predict_proba(X_val)[:, 1]

        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(p_val_raw, y_val)
        p_cal = np.clip(iso.predict(p_val_raw), 0, 1)

        ece = self._compute_ece(p_cal, y_val)
        brier = self._compute_brier(p_cal, y_val)
        accuracy = float(np.mean((p_cal >= 0.5) == y_val))

        # Per-class metrics
        op_mask = y_val == 0
        ex_mask = y_val == 1
        noise_fpr = float(np.mean(p_cal[op_mask] >= 0.5)) if op_mask.sum() > 0 else 0.0
        collapse_recall = float(np.mean(p_cal[ex_mask] >= 0.5)) if ex_mask.sum() > 0 else 0.0

        self._scorer = scorer
        self._isotonic = iso
        self.threshold = 0.5

        return CalibrationResult(
            ece=round(ece, 4),
            brier=round(brier, 4),
            accuracy=round(accuracy, 4),
            threshold=0.5,
            noise_fpr=round(noise_fpr, 4),
            collapse_recall=round(collapse_recall, 4),
            n_synthetic=len(X),
            ece_method="isotonic",
        )


class Discriminant:
    """Trajectory-aware pressure classification with structured result.

    Returns DiscriminantResult with full evidence trail.
    Hysteresis: min_consecutive_existential steps before allowing TRANSFORMATION.
    Hard guard: sustained collapse overrides uncertainty gate.
    """

    def __init__(
        self,
        viability: ViabilityKernel | None = None,
        coherence_critical: float = 0.15,
        drift_threshold: float = 0.5,
        min_consecutive_existential: int = 3,
        hard_guard_consecutive: int = 5,
    ) -> None:
        self.viability = viability or ViabilityKernel()
        self.coherence_critical = coherence_critical
        self.drift_threshold = drift_threshold
        self.min_consecutive_existential = min_consecutive_existential
        self.hard_guard_consecutive = hard_guard_consecutive
        self.trajectory = TrajectoryDiscriminant()
        self._consecutive_existential: int = 0
        self._consecutive_collapsing: int = 0

    def classify(
        self,
        phi: float,
        tau: float,
        x: np.ndarray,
        norm: NormSpace,
        phase_is_collapsing: bool,
        coherence: float,
        horizon: int = 10,
        phi_trend: float = 0.0,
        failure_density: float = 0.0,
        steps_in_bad_phase: int = 0,
    ) -> PressureKind:
        """Backward-compatible classify returning PressureKind only."""
        result = self.classify_detailed(
            phi, tau, x, norm, phase_is_collapsing, coherence,
            horizon, phi_trend, failure_density, steps_in_bad_phase,
        )
        return result.pressure

    def classify_detailed(
        self,
        phi: float,
        tau: float,
        x: np.ndarray,
        norm: NormSpace,
        phase_is_collapsing: bool,
        coherence: float,
        horizon: int = 10,
        phi_trend: float = 0.0,
        failure_density: float = 0.0,
        steps_in_bad_phase: int = 0,
    ) -> DiscriminantResult:
        """Classify with full structured evidence."""
        # Track sustained collapse for hard guard
        if phase_is_collapsing:
            self._consecutive_collapsing += 1
        else:
            self._consecutive_collapsing = max(0, self._consecutive_collapsing - 1)

        # Trajectory classifier
        kind, prob, uncertainty = self.trajectory.classify(
            phi, phi_trend, failure_density, coherence, steps_in_bad_phase,
        )

        explanation_parts: list[str] = []

        # Hard guard: sustained collapse with critical coherence
        hard_guard = (
            self._consecutive_collapsing >= self.hard_guard_consecutive
            and coherence < self.coherence_critical
        )
        if hard_guard:
            kind = PressureKind.EXISTENTIAL
            explanation_parts.append(
                f"HARD_GUARD: {self._consecutive_collapsing} consecutive collapses, "
                f"coherence={coherence:.3f}<{self.coherence_critical}"
            )

        # Critical coherence collapse (still requires collapsing phase)
        if phase_is_collapsing and coherence < self.coherence_critical:
            kind = PressureKind.EXISTENTIAL
            explanation_parts.append(f"CRITICAL_COHERENCE: {coherence:.3f}")

        # PRIMARY: phi >= tau (trajectory-accumulated evidence)
        if phi >= tau:
            kind = PressureKind.EXISTENTIAL
            explanation_parts.append(f"PHI_EXCEEDS_TAU: phi={phi:.3f}>=tau={tau:.3f}")

        # Hysteresis
        if kind == PressureKind.EXISTENTIAL:
            self._consecutive_existential += 1
        else:
            self._consecutive_existential = max(0, self._consecutive_existential - 1)

        hysteresis_blocked = (
            kind == PressureKind.EXISTENTIAL
            and self._consecutive_existential < self.min_consecutive_existential
            and not hard_guard  # hard guard bypasses hysteresis
        )

        if hysteresis_blocked:
            final = PressureKind.OPERATIONAL
            explanation_parts.append(
                f"HYSTERESIS: {self._consecutive_existential}/{self.min_consecutive_existential}"
            )
        else:
            final = kind

        if not explanation_parts:
            explanation_parts.append(
                f"TRAJECTORY: p={prob:.3f} u={uncertainty:.3f} "
                f"{'EXISTENTIAL' if final == PressureKind.EXISTENTIAL else 'OPERATIONAL'}"
            )

        return DiscriminantResult(
            pressure=final,
            probability_existential=prob,
            uncertainty=uncertainty,
            hard_guard_triggered=hard_guard,
            consecutive_existential=self._consecutive_existential,
            hysteresis_blocked=hysteresis_blocked,
            explanation=" | ".join(explanation_parts),
        )

    def mode_from_state(
        self,
        pressure: PressureKind,
        x: np.ndarray,
        norm: NormSpace,
        norm_origin: NormSpace,
    ) -> SystemMode:
        if pressure == PressureKind.EXISTENTIAL:
            return SystemMode.TRANSFORMATION
        if not norm.contains(x):
            return SystemMode.RECOVERY
        drift = norm.drift_from_origin(norm_origin)
        if drift > self.drift_threshold:
            return SystemMode.ADAPTATION
        return SystemMode.IDLE
