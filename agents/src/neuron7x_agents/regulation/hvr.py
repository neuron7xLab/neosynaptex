"""
Hormonal Vector Regulation — executable control theory for agent homeostasis.

This is not a metaphor. Every function maps to a numbered equation in the
SERO whitepaper. The system maintains agent throughput under stress via:

    Eq.3  T(t) = max(T_min, T_0 · (1 - α · Ŝ(t)))     Throughput
    Eq.4  ∀t: T(t) ≥ T_min > 0                          Safety invariant
    Eq.6  Ŝ(t) = Σ s_i · u_i(t) / Σ s_i                Stress estimator
    Eq.7  Ŝ(t) ← Ŝ(t-1) + γ · (Ŝ_raw - Ŝ(t-1))       Damping

Key properties:
    - T_min > 0 guaranteed by construction (never fully crashes)
    - Damping prevents oscillation (no flip-flop load shedding)
    - Severity weights derived from SLO thresholds (not vibes)
    - α is the critical tuning parameter (safe range: 0.30-0.55)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HVRConfig:
    """
    Hormonal Vector Regulation parameters.

    Parameters
    ----------
    t_0 : float
        Baseline throughput (normalized to 1.0).
    t_min : float
        Safety floor — throughput never drops below this.
    alpha : float
        Stress sensitivity. Safe range: [0.30, 0.55].
        COMA at α ≥ 0.45, OVERREACTION at α ≥ 0.55.
    gamma : float
        Damping coefficient. Safe range: [0.15, 0.50].
    s_max : float
        Stress ceiling for normalization.
    """

    t_0: float = 1.0
    t_min: float = 0.05
    alpha: float = 0.50
    gamma: float = 0.30
    s_max: float = 10.0

    def __post_init__(self) -> None:
        if self.t_min <= 0:
            msg = f"t_min must be > 0 (safety invariant Eq.4), got {self.t_min}"
            raise ValueError(msg)
        if not 0 < self.alpha < 1:
            msg = f"alpha must be in (0, 1), got {self.alpha}"
            raise ValueError(msg)
        if not 0 < self.gamma <= 1:
            msg = f"gamma must be in (0, 1], got {self.gamma}"
            raise ValueError(msg)


@dataclass
class StressState:
    """Current stress state of the system."""

    raw_stress: float = 0.0  # Ŝ_raw — before damping
    damped_stress: float = 0.0  # Ŝ(t) — after damping (Eq.7)
    throughput: float = 1.0  # T(t) — current throughput (Eq.3)
    tick: int = 0
    history: list[float] = field(default_factory=list)

    @property
    def is_stressed(self) -> bool:
        """True if damped stress exceeds 50% of capacity."""
        return self.damped_stress > 0.5

    @property
    def is_critical(self) -> bool:
        """True if throughput is within 2x of safety floor."""
        return self.throughput < 0.10


@dataclass
class SeverityWeight:
    """A single SLI channel with its severity weight derived from SLO."""

    name: str
    severity: float  # s_i — derived from 1/SLO_threshold
    current_value: float = 0.0  # u_i(t) — normalized deviation

    @property
    def contribution(self) -> float:
        """Weighted stress contribution: s_i × u_i."""
        return self.severity * self.current_value


class HormonalRegulator:
    """
    SERO Hormonal Vector Regulation engine.

    Maintains agent throughput under stress through biologically-inspired
    damped control with guaranteed safety floor.

    Parameters
    ----------
    config : HVRConfig
        Regulation parameters.

    Examples
    --------
    >>> reg = HormonalRegulator()
    >>> state = reg.tick([
    ...     SeverityWeight("error_rate", severity=100.0, current_value=0.3),
    ...     SeverityWeight("latency_p95", severity=5.0, current_value=0.1),
    ... ])
    >>> state.throughput > 0.05  # safety invariant holds
    True

    Invariants
    ----------
    - ∀t: state.throughput ≥ config.t_min  (Eq.4, guaranteed by construction)
    - Damping prevents oscillation (Eq.7, exponential smoothing)
    - Stress is bounded: 0 ≤ Ŝ ≤ s_max (clamped)
    """

    def __init__(self, config: HVRConfig | None = None) -> None:
        self.config = config or HVRConfig()
        self._state = StressState(throughput=self.config.t_0)

    @property
    def state(self) -> StressState:
        """Current stress state (read-only view)."""
        return self._state

    def _compute_raw_stress(self, channels: list[SeverityWeight]) -> float:
        """Eq.6: Ŝ_raw = Σ(s_i · u_i) / Σ(s_i)."""
        total_severity = sum(c.severity for c in channels)
        if total_severity == 0:
            return 0.0
        weighted_sum = sum(c.contribution for c in channels)
        return min(self.config.s_max, max(0.0, weighted_sum / total_severity))

    def _damp(self, raw: float) -> float:
        """Eq.7: Ŝ(t) ← Ŝ(t-1) + γ · (Ŝ_raw - Ŝ(t-1))."""
        return self._state.damped_stress + self.config.gamma * (raw - self._state.damped_stress)

    def _compute_throughput(self, damped_stress: float) -> float:
        """Eq.3: T(t) = max(T_min, T_0 · (1 - α · Ŝ(t)))."""
        raw_t = self.config.t_0 * (1.0 - self.config.alpha * damped_stress)
        return max(self.config.t_min, raw_t)  # Eq.4: safety invariant

    def tick(self, channels: list[SeverityWeight]) -> StressState:
        """
        Advance one regulation cycle.

        Parameters
        ----------
        channels : list[SeverityWeight]
            Current SLI channel readings.

        Returns
        -------
        StressState
            Updated stress state with throughput.
        """
        raw = self._compute_raw_stress(channels)
        damped = self._damp(raw)
        throughput = self._compute_throughput(damped)

        self._state = StressState(
            raw_stress=raw,
            damped_stress=damped,
            throughput=throughput,
            tick=self._state.tick + 1,
            history=[*self._state.history[-999:], throughput],
        )
        return self._state

    def reset(self) -> None:
        """Reset to baseline state."""
        self._state = StressState(throughput=self.config.t_0)

    def safety_invariant_holds(self) -> bool:
        """Verify Eq.4: T(t) ≥ T_min at all recorded ticks."""
        return all(t >= self.config.t_min for t in self._state.history)
