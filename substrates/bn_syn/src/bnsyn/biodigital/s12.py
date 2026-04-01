"""BIO-DIGITAL-S12 deterministic signal and gate helpers.

Implements bounded, replayable update rules derived from the
BIO-DIGITAL-S12 catalog for in-silico control loops.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Literal


_EPSILON = 1e-12
_AGENT_MODES = {"explore", "exploit", "verify", "stop"}


def _validate_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def _validate_non_negative(name: str, value: float) -> None:
    if value < 0.0:
        raise ValueError(f"{name} must be >= 0, got {value}")


def clamp01(value: float) -> float:
    """Clamp value to [0, 1]."""
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class AllostasisState:
    """Bounded deterministic allostasis state (AL)."""

    horizon_steps: int
    forecast_vector: tuple[float, ...]
    target_vector: tuple[float, ...]


@dataclass(frozen=True)
class ThermostatState:
    """Landauer thermostat state."""

    erased_bits_proxy: float
    entropy_budget: float
    t_max: float

    def __post_init__(self) -> None:
        _validate_non_negative("erased_bits_proxy", self.erased_bits_proxy)
        if self.entropy_budget <= 0.0:
            raise ValueError(f"entropy_budget must be > 0, got {self.entropy_budget}")
        _validate_unit_interval("t_max", self.t_max)


@dataclass(frozen=True)
class ThermostatReport:
    """Thermostat action report."""

    temperature_proxy: float
    triggered: bool
    stress_guard: float
    mode: str
    cache_flushed: bool
    candidate_expansion_blocked: bool


@dataclass(frozen=True)
class BioSignalState:
    """Current bounded scalar bio-signals."""

    u: float
    a: float
    r: float
    s: float
    o: float
    t: float

    def __post_init__(self) -> None:
        _validate_unit_interval("u", self.u)
        _validate_unit_interval("a", self.a)
        _validate_unit_interval("s", self.s)
        _validate_unit_interval("o", self.o)
        _validate_unit_interval("t", self.t)
        if not -1.0 <= self.r <= 1.0:
            raise ValueError(f"r must be in [-1, 1], got {self.r}")


@dataclass(frozen=True)
class NeuroConsistencyReport:
    """Gate output for G.BIO.001."""

    pass_gate: bool
    r_effective: float
    violations: tuple[str, ...]


def normalized_shannon_entropy(distribution: list[float]) -> float:
    """Compute Shannon entropy normalized to [0, 1] for a finite distribution."""
    if not distribution:
        raise ValueError("distribution must not be empty")
    if any(value < 0.0 for value in distribution):
        raise ValueError("distribution must not contain negative values")

    positives = [x for x in distribution if x > 0.0]
    total = sum(positives)
    if total <= _EPSILON:
        return 0.0

    probs = [x / total for x in positives]
    entropy = -sum(p * log2(p) for p in probs)
    max_entropy = log2(len(probs)) if len(probs) > 1 else 1.0
    return clamp01(entropy / max_entropy)


def update_ach_uncertainty(u_base: float, k_u: float, h_q_norm: float) -> float:
    """Entropy-curiosity coupler: u := clamp01(u_base + k_u * H_Q_norm)."""
    return clamp01(u_base + (k_u * h_q_norm))


def update_oxt_coherence(
    o_base: float,
    k_o: float,
    coherence_score: float,
    conflict_score: float,
) -> float:
    """Update OXT coherence signal using deterministic linear coupling."""
    return clamp01(o_base + (k_o * (coherence_score - conflict_score)))


def update_5ht_impulse_control(
    t_base: float,
    k_t: float,
    stability_need: float,
    immediate_gain_pressure: float,
) -> float:
    """Update 5HT impulse control with bounded coupling."""
    return clamp01(t_base + (k_t * (stability_need - immediate_gain_pressure)))


def al_update(
    metrics: tuple[float, ...],
    budgets: tuple[float, ...],
    history: tuple[float, ...],
    horizon_steps: int,
) -> AllostasisState:
    """Deterministic bounded AL update without unbounded search."""
    if horizon_steps < 1:
        raise ValueError("horizon_steps must be >= 1")
    if not metrics:
        raise ValueError("metrics must not be empty")
    if not budgets:
        raise ValueError("budgets must not be empty")
    if not history:
        raise ValueError("history must not be empty")

    mean_metric = sum(metrics) / max(1, len(metrics))
    mean_budget = sum(budgets) / max(1, len(budgets))
    history_tail = history[-horizon_steps:]
    mean_history = sum(history_tail) / max(1, len(history_tail))

    forecast = tuple(mean_metric for _ in range(horizon_steps))
    target = tuple(max(0.0, min(mean_budget, mean_history)) for _ in range(len(metrics)))
    return AllostasisState(
        horizon_steps=horizon_steps,
        forecast_vector=forecast,
        target_vector=target,
    )


def landauer_thermostat(state: ThermostatState) -> ThermostatReport:
    """Apply M_LANDAUER_THERMOSTAT deterministic trigger rule."""
    budget = max(1.0, state.entropy_budget)
    temperature = state.erased_bits_proxy / budget
    triggered = temperature >= state.t_max or state.erased_bits_proxy >= state.entropy_budget
    if triggered:
        return ThermostatReport(
            temperature_proxy=temperature,
            triggered=True,
            stress_guard=1.0,
            mode="verify",
            cache_flushed=True,
            candidate_expansion_blocked=True,
        )
    return ThermostatReport(
        temperature_proxy=temperature,
        triggered=False,
        stress_guard=0.0,
        mode="explore",
        cache_flushed=False,
        candidate_expansion_blocked=False,
    )


def evaluate_neuro_consistency(
    signals: BioSignalState,
    mode: Literal["explore", "exploit", "verify", "stop"],
    allow_external_sources: bool,
    require_extra_certificates: bool,
    s_hi: float = 0.9,
    t_hi: float = 0.8,
    o_lo: float = 0.2,
) -> NeuroConsistencyReport:
    """Evaluate G.BIO.001 consistency rules and derive r_effective."""
    if mode not in _AGENT_MODES:
        raise ValueError(f"mode must be one of {_AGENT_MODES}, got {mode}")
    _validate_unit_interval("s_hi", s_hi)
    _validate_unit_interval("t_hi", t_hi)
    _validate_unit_interval("o_lo", o_lo)

    violations: list[str] = []
    r_effective = signals.r

    if signals.s >= s_hi:
        r_effective = 0.0
        if mode not in {"verify", "stop"}:
            violations.append("mode_incompatible_with_stress_guard")

    if signals.t >= t_hi and not require_extra_certificates:
        violations.append("high_impulse_requires_extra_certificates")

    if signals.o <= o_lo and allow_external_sources:
        violations.append("low_coherence_forbids_untrusted_external_sources")

    return NeuroConsistencyReport(
        pass_gate=not violations,
        r_effective=r_effective,
        violations=tuple(violations),
    )
