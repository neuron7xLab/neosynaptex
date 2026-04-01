"""Adaptive descriptor extrapolation forecast for field evolution."""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.detection_config import (
    DAMPING_BASE,
    DAMPING_MAX,
    FIELD_CLIP_MAX,
    FIELD_CLIP_MIN,
    FLUIDITY_COEFF_DEFAULT,
    STRUCTURAL_ERROR_WEIGHT,
    UNCERTAINTY_W_CONNECTIVITY,
    UNCERTAINTY_W_DESENSITIZATION,
    UNCERTAINTY_W_PLASTICITY,
)

# Numerical stability constants
_NUMERICAL_DIVISOR_GUARD: float = 1e-12  # [PHYS] Prevents division by zero in OLS

from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec
from mycelium_fractal_net.types.forecast import (
    ForecastResult,
    TrajectoryStep,
    UncertaintyEnvelope,
)

__all__ = ['counterfactual', 'forecast_next', 'forecast_regime']

def _history_windows(history: np.ndarray) -> list[np.ndarray]:
    if history.shape[0] < 3:
        return [history]
    candidates = [history[-min(k, history.shape[0]) :] for k in (3, 5, 8)]
    unique: list[np.ndarray] = []
    seen: set[int] = set()
    for item in candidates:
        key = item.shape[0]
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _adaptive_damping(sequence: FieldSequence) -> float:
    descriptor = compute_morphology_descriptor(sequence)
    plasticity_index = float(descriptor.neuromodulation.get("plasticity_index", 0.0))
    fluidity_coeff = FLUIDITY_COEFF_DEFAULT
    if sequence.spec is not None and sequence.spec.neuromodulation is not None:
        fluidity_coeff = max(
            fluidity_coeff, float(sequence.spec.neuromodulation.gain_fluidity_coeff)
        )
        if sequence.spec.neuromodulation.serotonergic is not None:
            fluidity_coeff = max(
                fluidity_coeff,
                float(sequence.spec.neuromodulation.serotonergic.gain_fluidity_coeff),
            )
    damping = DAMPING_BASE + fluidity_coeff * plasticity_index
    return float(np.clip(damping, DAMPING_BASE, DAMPING_MAX))


def _project_from_window(window: np.ndarray, horizon: int, damping: float) -> np.ndarray:
    """AR(1) projection: x_{t+1} = mean + phi * (x_t - mean) + residual decay.

    Estimates the AR(1) coefficient phi from the window, then projects
    forward with exponential damping on the innovation term.
    Falls back to mean-reversion for very short windows.
    """
    if window.shape[0] < 2:
        return np.repeat(window[-1][None, :, :], horizon, axis=0)

    # Estimate AR(1) parameters per-cell: x_t = mu + phi * (x_{t-1} - mu)
    mean_field = np.mean(window, axis=0)
    centered = window - mean_field

    if window.shape[0] >= 3:
        # OLS estimate of phi: phi = sum(x_t * x_{t-1}) / sum(x_{t-1}^2)
        numerator = np.sum(centered[1:] * centered[:-1], axis=0)
        denominator = np.sum(centered[:-1] ** 2, axis=0) + _NUMERICAL_DIVISOR_GUARD
        phi = np.clip(numerator / denominator, -0.99, 0.99)
    else:
        # Fallback: use damping as phi proxy
        phi = np.full_like(mean_field, damping)

    # Also compute mean innovation (trend) for short-term accuracy
    delta = np.mean(np.diff(window, axis=0), axis=0)

    current = window[-1].astype(np.float64).copy()
    frames = []
    for step in range(1, horizon + 1):
        decay = damping ** (step - 1)
        # AR(1) mean-reversion + damped trend
        ar1_pull = mean_field + phi * (current - mean_field)
        trend_push = current + delta * decay
        # Blend: AR(1) dominates at longer horizons, trend at short
        blend = min(1.0, step / max(1, horizon))
        current = (1.0 - blend) * trend_push + blend * ar1_pull
        current = np.clip(current, FIELD_CLIP_MIN, FIELD_CLIP_MAX)
        frames.append(current.copy())
    return np.stack(frames, axis=0)


def _desensitization_lag(sequence: FieldSequence) -> float:
    spec = sequence.spec.neuromodulation if sequence.spec is not None else None
    if spec is None or spec.gabaa_tonic is None:
        return 0.0
    return max(
        0.0,
        float(spec.gabaa_tonic.desensitization_rate_hz - spec.gabaa_tonic.recovery_rate_hz),
    )


def _roll_forward(
    sequence: FieldSequence,
    horizon: int,
    descriptor: object = None,
) -> tuple[np.ndarray, UncertaintyEnvelope, float]:
    damping = _adaptive_damping(sequence)
    if descriptor is None:
        descriptor = compute_morphology_descriptor(sequence)
    plasticity_index = float(descriptor.neuromodulation.get("plasticity_index", 0.0))
    connectivity_divergence = float(descriptor.connectivity.get("connectivity_divergence", 0.0))
    des_lag = _desensitization_lag(sequence)
    if sequence.history is None or sequence.history.shape[0] < 2:
        stack = np.repeat(sequence.field[None, :, :], horizon, axis=0)
        envelope = UncertaintyEnvelope(
            plasticity_index=plasticity_index,
            connectivity_divergence=connectivity_divergence,
            desensitization_lag=des_lag,
        )
        return stack, envelope, damping
    windows = _history_windows(sequence.history.astype(np.float64))
    projections = np.stack(
        [_project_from_window(window, horizon, damping) for window in windows], axis=0
    )
    mean_projection = np.mean(projections, axis=0)
    uncertainty_scale = (
        1.0
        + UNCERTAINTY_W_PLASTICITY * plasticity_index
        + UNCERTAINTY_W_CONNECTIVITY * connectivity_divergence
        + UNCERTAINTY_W_DESENSITIZATION * des_lag
    )
    envelope = UncertaintyEnvelope(
        ensemble_std_mV=float(np.std(projections[:, -1]) * 1000.0 * uncertainty_scale),
        ensemble_range_mV=float(
            (np.max(projections[:, -1]) - np.min(projections[:, -1])) * 1000.0 * uncertainty_scale
        ),
        plasticity_index=plasticity_index,
        connectivity_divergence=connectivity_divergence,
        desensitization_lag=des_lag,
    )
    return mean_projection, envelope, damping


def forecast_next(
    sequence: FieldSequence,
    horizon: int = 8,
    descriptor: object = None,
) -> ForecastResult:
    horizon = max(1, int(horizon))
    stack, uncertainty_envelope, damping = _roll_forward(sequence, horizon, descriptor=descriptor)
    final = stack[-1]
    trajectory: list[TrajectoryStep] = []
    for frame in stack:
        descriptor = compute_morphology_descriptor(
            FieldSequence(
                field=frame,
                history=None,
                spec=sequence.spec,
                metadata=sequence.metadata,
            )
        )
        trajectory.append(
            TrajectoryStep(
                D_box=descriptor.features.get("D_box", 0.0),
                f_active=descriptor.features.get("f_active", 0.0),
                volatility=descriptor.temporal.get("volatility", 0.0),
                connectivity_divergence=descriptor.connectivity.get("connectivity_divergence", 0.0),
                plasticity_index=descriptor.neuromodulation.get("plasticity_index", 0.0),
                field_mean_mV=float(np.mean(frame) * 1000.0),
            )
        )
    if descriptor is None:
        descriptor = compute_morphology_descriptor(sequence)
    last_step = trajectory[-1]
    descriptor_shift = float(abs(last_step.D_box - descriptor.features.get("D_box", 0.0)))
    activity_shift = float(abs(last_step.f_active - descriptor.features.get("f_active", 0.0)))
    forecast_structural_error = float(STRUCTURAL_ERROR_WEIGHT * (descriptor_shift + activity_shift))
    benchmark_metrics = {
        "descriptor_shift": descriptor_shift,
        "activity_shift": activity_shift,
        "forecast_structural_error": forecast_structural_error,
        "adaptive_damping": damping,
    }
    evaluation_metrics = {
        "forecast_uncertainty_mV": uncertainty_envelope.ensemble_std_mV,
        "forecast_range_mV": uncertainty_envelope.ensemble_range_mV,
        "horizon": float(horizon),
        "adaptive_damping": damping,
        "plasticity_index": uncertainty_envelope.plasticity_index,
        "connectivity_divergence": uncertainty_envelope.connectivity_divergence,
        "desensitization_lag": uncertainty_envelope.desensitization_lag,
    }
    return ForecastResult(
        version="mfn-forecast-v3",
        horizon=horizon,
        method="adaptive_descriptor_extrapolation",
        uncertainty_envelope=uncertainty_envelope.to_dict(),
        descriptor_trajectory=[step.to_dict() for step in trajectory],
        predicted_states=stack.tolist(),
        predicted_state_summary={
            "field_min_mV": float(np.min(final) * 1000.0),
            "field_max_mV": float(np.max(final) * 1000.0),
            "field_mean_mV": float(np.mean(final) * 1000.0),
            "field_std_mV": float(np.std(final) * 1000.0),
        },
        evaluation_metrics=evaluation_metrics,
        benchmark_metrics=benchmark_metrics,
        metadata={"runtime_hash": sequence.runtime_hash},
    )


def forecast_regime(sequence: FieldSequence, horizon: int = 8) -> ForecastResult:
    return forecast_next(sequence, horizon=horizon)


def counterfactual(sequence: FieldSequence, modified_spec: SimulationSpec) -> ForecastResult:
    candidate = FieldSequence(
        field=sequence.field,
        history=sequence.history,
        spec=modified_spec,
        metadata={"counterfactual": True},
    )
    horizon = max(1, min(16, modified_spec.steps or 8))
    result = forecast_next(candidate, horizon=horizon)
    mode = "baseline"
    if modified_spec.neuromodulation is not None:
        profile = modified_spec.neuromodulation.profile
        if "gabaa" in profile:
            mode = "gabaa-tonic"
        elif "serotonergic" in profile:
            mode = "serotonergic"
        elif "criticality" in profile:
            mode = "balanced-criticality"
    metadata = dict(result.metadata)
    metadata["counterfactual_mode"] = mode
    return ForecastResult(
        version=result.version,
        horizon=result.horizon,
        method=result.method,
        uncertainty_envelope=result.uncertainty_envelope,
        descriptor_trajectory=result.descriptor_trajectory,
        predicted_states=result.predicted_states,
        predicted_state_summary=result.predicted_state_summary,
        evaluation_metrics=result.evaluation_metrics,
        benchmark_metrics=result.benchmark_metrics,
        metadata=metadata,
    )
