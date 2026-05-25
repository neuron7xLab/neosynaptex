"""Deterministic Reflex Engine (DRE) with AST-segregation reflex gates."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import NamedTuple, cast

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "BehavioralStateVector",
    "ConstitutionInvariant",
    "DREConfig",
    "DREDecision",
    "DREInput",
    "DREState",
    "compute_forcing_vector",
    "kl_divergence",
    "run_dre_loop",
]

_EPS = 1e-12
_J_SHAPE = (7, 7)
_UINT32_MAX = np.iinfo(np.uint32).max
_UINT64_MAX = np.iinfo(np.uint64).max
FloatArray = NDArray[np.float64]


class BehavioralStateVector(NamedTuple):
    timestamp_ns: np.uint64
    state_id: np.uint32
    friction_coefficient: np.float32
    trajectory_jacobian: FloatArray
    execution_velocity: np.float32


@dataclass(frozen=True)
class DREConfig:
    kl_threshold: float = 0.25
    risk_threshold_tau: float = 0.2
    friction_gain: float = 0.1
    phase_transition_days: int = 7
    max_ktb_events: int = 1024


@dataclass(frozen=True)
class ConstitutionInvariant:
    allowed_actions: tuple[str, ...]
    max_action_magnitude: float


@dataclass(frozen=True)
class DREInput:
    model_self: tuple[float, ...]
    model_other: tuple[float, ...]
    expected_free_energy: float
    action: str
    action_magnitude: float
    efferent_copy: tuple[float, ...]
    timestamp_ns: int
    state_id: int
    execution_velocity: float


@dataclass(frozen=True)
class DREDecision:
    accepted: bool
    reason: str
    kl_value: float
    friction: float
    quarantine_external: bool


@dataclass(frozen=True)
class DREState:
    day_index: int
    ktb: tuple[BehavioralStateVector, ...]
    phase_transition_triggered: bool


def _check_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _check_non_negative_finite(name: str, value: float) -> None:
    _check_finite(name, value)
    if value < 0.0:
        raise ValueError(f"{name} must be >= 0")


def _as_finite_distribution(name: str, model: Sequence[float]) -> FloatArray:
    arr = np.asarray(model, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name} must be a non-empty 1D vector")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    if np.any(arr < 0.0):
        raise ValueError("model distributions must be non-negative")
    total = float(np.sum(arr))
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError(f"{name} must have positive finite mass")
    return cast(FloatArray, arr / total)


def _validate_config(config: DREConfig) -> None:
    _check_non_negative_finite("config.kl_threshold", config.kl_threshold)
    _check_non_negative_finite("config.risk_threshold_tau", config.risk_threshold_tau)
    _check_non_negative_finite("config.friction_gain", config.friction_gain)
    if config.phase_transition_days < 1:
        raise ValueError("phase_transition_days must be >= 1")
    if config.max_ktb_events < 1:
        raise ValueError("max_ktb_events must be >= 1")


def _validate_input(inp: DREInput) -> None:
    _check_non_negative_finite("expected_free_energy", inp.expected_free_energy)
    _check_non_negative_finite("action_magnitude", inp.action_magnitude)
    _check_finite("execution_velocity", inp.execution_velocity)
    if not (0 <= inp.timestamp_ns <= _UINT64_MAX):
        raise ValueError("timestamp_ns must fit uint64 without wraparound")
    if not (0 <= inp.state_id <= _UINT32_MAX):
        raise ValueError("state_id must fit uint32 without wraparound")


def kl_divergence(model_other: Sequence[float], model_self: Sequence[float]) -> float:
    q = _as_finite_distribution("model_other", model_other)
    p = _as_finite_distribution("model_self", model_self)
    if q.size != p.size:
        raise ValueError("model vectors must have equal length")
    value = float(np.sum(q * (np.log(q + _EPS) - np.log(p + _EPS))))
    if not math.isfinite(value):
        raise ValueError("kl_divergence result must be finite")
    return value


def _validate_constitution(
    action: str,
    magnitude: float,
    invariant: ConstitutionInvariant,
) -> bool:
    _check_non_negative_finite("invariant.max_action_magnitude", invariant.max_action_magnitude)
    return (
        magnitude >= 0.0
        and action in invariant.allowed_actions
        and magnitude <= invariant.max_action_magnitude
    )


def _ast_segmentation_mask(v_ext: Sequence[float], efferent_copy: Sequence[float]) -> bool:
    ext = np.asarray(v_ext, dtype=np.float64)
    eff = np.asarray(efferent_copy, dtype=np.float64)
    if ext.ndim != 1 or eff.ndim != 1:
        raise ValueError("model_other and efferent_copy must be 1D vectors")
    if ext.shape != eff.shape:
        raise ValueError("efferent_copy shape must match model_other shape")
    if not np.all(np.isfinite(ext)) or not np.all(np.isfinite(eff)):
        raise ValueError("model_other and efferent_copy must contain only finite values")
    mask = ext * eff
    return bool(np.any(np.abs(mask) > 0.0))


def _make_behavior_vector(
    *,
    inp: DREInput,
    friction: float,
    kl_value: float,
) -> BehavioralStateVector:
    _validate_input(inp)
    _check_non_negative_finite("friction", friction)
    _check_non_negative_finite("kl_value", kl_value)
    jac: FloatArray = np.eye(_J_SHAPE[0], dtype=np.float64) * min(1.0, kl_value + friction)
    return BehavioralStateVector(
        timestamp_ns=np.uint64(inp.timestamp_ns),
        state_id=np.uint32(inp.state_id),
        friction_coefficient=np.float32(friction),
        trajectory_jacobian=jac,
        execution_velocity=np.float32(inp.execution_velocity),
    )


def _evaluate_atom(
    inp: DREInput,
    config: DREConfig,
    invariant: ConstitutionInvariant,
) -> DREDecision:
    _validate_input(inp)
    kl_value = kl_divergence(inp.model_other, inp.model_self)
    friction = min(1.0, config.friction_gain * (1.0 + kl_value))

    if not _ast_segmentation_mask(inp.model_other, inp.efferent_copy):
        return DREDecision(False, "blocked:quarantine_external", kl_value, friction, True)
    if kl_value > config.kl_threshold:
        return DREDecision(False, "blocked:input_kl_drift", kl_value, friction, False)
    if inp.expected_free_energy >= config.risk_threshold_tau:
        return DREDecision(False, "blocked:fail_closed_risk_gate", kl_value, friction, False)
    if not _validate_constitution(inp.action, inp.action_magnitude, invariant):
        return DREDecision(False, "blocked:dlpfc_invariant", kl_value, friction, False)
    return DREDecision(True, "accepted", kl_value, friction, False)


def _push_ktb(
    ktb: list[BehavioralStateVector],
    event: BehavioralStateVector,
    max_events: int,
) -> None:
    if max_events < 1:
        raise ValueError("max_ktb_events must be >= 1")
    if len(ktb) >= max_events:
        ktb.pop(0)
    ktb.append(event)


def compute_forcing_vector(ktb: Sequence[BehavioralStateVector]) -> FloatArray:
    """Compute environment forcing vector F_env from KTB jacobians via SVD."""
    if not ktb:
        return np.zeros(_J_SHAPE[0], dtype=np.float64)
    mats = np.stack([row.trajectory_jacobian.astype(np.float64) for row in ktb], axis=0)
    if mats.shape[1:] != _J_SHAPE:
        raise ValueError(f"trajectory_jacobian must have shape {_J_SHAPE}")
    if not np.all(np.isfinite(mats)):
        raise ValueError("trajectory_jacobian must contain only finite values")
    j_behav = np.mean(mats, axis=0)
    _, s, vt = np.linalg.svd(j_behav, full_matrices=False)
    inv_s = np.diag(1.0 / (s + _EPS))
    forcing = vt.T @ inv_s
    return cast(FloatArray, forcing[:, 0])


async def run_dre_loop(
    stream: Iterable[DREInput],
    *,
    config: DREConfig,
    invariant: ConstitutionInvariant,
    start_day_index: int = 0,
) -> tuple[list[DREDecision], DREState]:
    _validate_config(config)
    if start_day_index < 0:
        raise ValueError("start_day_index must be >= 0")

    decisions: list[DREDecision] = []
    ktb: list[BehavioralStateVector] = []
    day_index = start_day_index

    for item in stream:
        day_index += 1
        decision = _evaluate_atom(item, config, invariant)
        decisions.append(decision)
        if not decision.accepted:
            _push_ktb(
                ktb,
                _make_behavior_vector(
                    inp=item,
                    friction=decision.friction,
                    kl_value=decision.kl_value,
                ),
                config.max_ktb_events,
            )

    phase_transition_triggered = bool(ktb) and day_index >= config.phase_transition_days
    state = DREState(
        day_index=day_index,
        ktb=tuple(ktb),
        phase_transition_triggered=phase_transition_triggered,
    )
    return decisions, state