"""Minimal truth-drift gate.

Activates only when:
1) environment drift is material, and
2) knowledge confidence is low.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.event_bus import AnomalyEvent, EventBus

__all__ = ["TruthGuardConfig", "TruthGuardDecision", "evaluate_truth_guard"]


@dataclass(frozen=True)
class TruthGuardConfig:
    drift_threshold: float = 0.2
    min_confidence: float = 0.6
    alert_domain: str = "architecture.truth_alert"


@dataclass(frozen=True)
class TruthGuardDecision:
    activated: bool
    drift: float
    reason: str


def evaluate_truth_guard(
    *,
    baseline: float,
    observed: float,
    confidence: float,
    config: TruthGuardConfig | None = None,
    event_bus: EventBus | None = None,
) -> TruthGuardDecision:
    """Evaluate truth risk under dynamic environment shift.

    All scalar inputs and thresholds are constrained to [0, 1].
    """
    config = config or TruthGuardConfig()

    _check_unit("baseline", baseline)
    _check_unit("observed", observed)
    _check_unit("confidence", confidence)
    _check_unit("config.drift_threshold", config.drift_threshold)
    _check_unit("config.min_confidence", config.min_confidence)
    if not config.alert_domain:
        raise ValueError("config.alert_domain must be non-empty")

    drift = abs(observed - baseline)
    activated = drift >= config.drift_threshold and confidence < config.min_confidence

    if activated:
        if event_bus is not None:
            event_bus.emit(
                AnomalyEvent(
                    domain=config.alert_domain,
                    metric="truth_drift",
                    value=drift,
                    threshold=config.drift_threshold,
                )
            )
        return TruthGuardDecision(True, drift, "dynamic_environment_drifted_truth")

    if drift >= config.drift_threshold:
        return TruthGuardDecision(False, drift, "drift_but_confidence_ok")
    if confidence < config.min_confidence:
        return TruthGuardDecision(False, drift, "confidence_low_but_drift_small")
    return TruthGuardDecision(False, drift, "stable")


def _check_unit(name: str, value: float) -> None:
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be in [0, 1], got {value}")
