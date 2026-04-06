"""Objection Energy Budget (OEB) controller — PID-regulated critic gain.

Task 3 deliverable.

Normalizes the strength/frequency of objections to avoid both under-critique
(hallucinations leak through) and over-critique (valid claims are falsely
rejected).  The controller adjusts *critic_gain* dynamically via a discrete
PID loop, subject to a finite energy budget per evaluation cycle.

Design notes
------------
* INV-1 compliant: γ is never cached as state on OEB.  ``critic_gain`` is
  the *only* internal gain; γ appears solely as an element of the
  ``CoherenceState`` vector produced by the state-space model.
* All snapshots are frozen dataclasses — immutable audit trail.
* numpy-only; no scipy dependency.

Integration
-----------
``simulate_with_oeb`` couples the OEB controller to a
``CoherenceStateSpace`` model: at each timestep the controller's
``critic_gain`` is converted to an objection-energy input ``u_E`` fed into
the state-space transition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
)

__all__ = [
    "ObjectionBudget",
    "OEBController",
    "simulate_with_oeb",
]

FloatArray = NDArray[np.float64]

# ------------------------------------------------------------------
# Immutable snapshot
# ------------------------------------------------------------------


@dataclass(frozen=True)
class ObjectionBudget:
    """Immutable snapshot of the objection-energy budget at one timestep.

    Attributes:
        energy_total: total OEB allocated for this cycle.
        energy_spent: energy already consumed.
        critic_gain: current gain multiplier for the critic.
        cycle: evaluation-cycle ordinal.
    """

    energy_total: float
    energy_spent: float
    critic_gain: float
    cycle: int

    def __post_init__(self) -> None:
        if self.energy_total < 0:
            raise ValueError("energy_total must be non-negative")
        if self.energy_spent < 0:
            raise ValueError("energy_spent must be non-negative")
        if self.critic_gain < 0:
            raise ValueError("critic_gain must be non-negative")
        if self.cycle < 0:
            raise ValueError("cycle must be non-negative")

    @property
    def energy_remaining(self) -> float:
        """Energy still available in this cycle."""
        return max(0.0, self.energy_total - self.energy_spent)


# ------------------------------------------------------------------
# PID controller
# ------------------------------------------------------------------

_DEFAULT_TARGET_HALLUC: Final[float] = 0.05


class OEBController:
    """PID-like controller that adjusts critic gain to balance hallucination
    rate against false-rejection rate, subject to a finite energy budget.

    Parameters
    ----------
    gain_kp : float
        Proportional gain for PID.
    gain_ki : float
        Integral gain for PID.
    gain_kd : float
        Derivative gain for PID.
    energy_per_cycle : float
        Total energy budget allocated at the start of each cycle.
    min_gain : float
        Lower clamp for critic_gain.
    max_gain : float
        Upper clamp for critic_gain.
    dt : float
        Timestep size (used for energy accounting and PID integration).
    target_hallucination_rate : float
        Setpoint for the hallucination-rate error signal.
    """

    def __init__(
        self,
        gain_kp: float = 1.0,
        gain_ki: float = 0.1,
        gain_kd: float = 0.05,
        energy_per_cycle: float = 10.0,
        min_gain: float = 0.1,
        max_gain: float = 5.0,
        dt: float = 0.1,
        target_hallucination_rate: float = _DEFAULT_TARGET_HALLUC,
    ) -> None:
        if energy_per_cycle < 0:
            raise ValueError("energy_per_cycle must be non-negative")
        if min_gain < 0:
            raise ValueError("min_gain must be non-negative")
        if max_gain < min_gain:
            raise ValueError("max_gain must be >= min_gain")
        if dt <= 0:
            raise ValueError("dt must be positive")

        self.gain_kp: Final[float] = gain_kp
        self.gain_ki: Final[float] = gain_ki
        self.gain_kd: Final[float] = gain_kd
        self.energy_per_cycle: Final[float] = energy_per_cycle
        self.min_gain: Final[float] = min_gain
        self.max_gain: Final[float] = max_gain
        self.dt: Final[float] = dt
        self.target_hallucination_rate: Final[float] = target_hallucination_rate

        # Mutable internal PID state
        self._critic_gain: float = 0.5 * (min_gain + max_gain)
        self._integral: float = 0.0
        self._prev_error: float = 0.0
        self._energy_spent: float = 0.0
        self._cycle: int = 0
        self._last_hallucination_rate: float = target_hallucination_rate

    # -- PID step ---------------------------------------------------

    def step(
        self,
        hallucination_rate: float,
        false_reject_rate: float,
    ) -> ObjectionBudget:
        """Advance the PID controller by one timestep.

        The error signal is ``hallucination_rate - target``.  A positive
        error (too many hallucinations) drives the gain *up*; however,
        ``false_reject_rate`` acts as a *penalty* that opposes gain
        increases when the critic is already over-zealous.

        Energy is deducted proportional to ``critic_gain * dt``.  If the
        budget is exhausted the gain is clamped to ``min_gain``.

        Returns an immutable :class:`ObjectionBudget` snapshot.
        """
        error = hallucination_rate - self.target_hallucination_rate
        # Penalise high false-reject: subtract it from error so PID
        # reduces gain when false_reject_rate is large.
        adjusted_error = error - false_reject_rate

        self._integral += adjusted_error * self.dt
        derivative = (adjusted_error - self._prev_error) / self.dt
        self._prev_error = adjusted_error

        pid_output = (
            self.gain_kp * adjusted_error
            + self.gain_ki * self._integral
            + self.gain_kd * derivative
        )

        self._critic_gain += pid_output * self.dt

        # Clamp to [min_gain, max_gain]
        self._critic_gain = float(np.clip(self._critic_gain, self.min_gain, self.max_gain))

        # Energy accounting
        energy_cost = self._critic_gain * self.dt
        self._energy_spent += energy_cost

        # If budget exhausted, force gain to minimum
        if self._energy_spent >= self.energy_per_cycle:
            self._energy_spent = self.energy_per_cycle
            self._critic_gain = self.min_gain

        self._last_hallucination_rate = hallucination_rate

        return ObjectionBudget(
            energy_total=self.energy_per_cycle,
            energy_spent=self._energy_spent,
            critic_gain=self._critic_gain,
            cycle=self._cycle,
        )

    # -- Cycle management -------------------------------------------

    def reset_cycle(self) -> None:
        """Start a new evaluation cycle with a fresh energy budget.

        PID integral state is preserved across cycles so that the
        controller retains memory of past behaviour.
        """
        self._cycle += 1
        self._energy_spent = 0.0

    # -- Rollout helper ---------------------------------------------

    def rollout(
        self,
        hallucination_rates: list[float] | FloatArray,
        false_reject_rates: list[float] | FloatArray,
    ) -> list[ObjectionBudget]:
        """Run N steps with the given rate sequences.

        Both sequences must have the same length.
        """
        h_arr = np.asarray(hallucination_rates, dtype=np.float64)
        f_arr = np.asarray(false_reject_rates, dtype=np.float64)
        if h_arr.shape != f_arr.shape or h_arr.ndim != 1:
            raise ValueError(
                "hallucination_rates and false_reject_rates must be 1-D arrays of the same length"
            )
        budgets: list[ObjectionBudget] = []
        for i in range(len(h_arr)):
            budgets.append(self.step(float(h_arr[i]), float(f_arr[i])))
        return budgets

    # -- Pareto point -----------------------------------------------

    def pareto_point(self) -> tuple[float, float, float]:
        """Return ``(quality, cost, gain)`` at the current operating point.

        * quality = 1 - last_hallucination_rate   (higher is better)
        * cost    = energy_spent                   (lower is better)
        * gain    = current critic_gain
        """
        quality = 1.0 - self._last_hallucination_rate
        return (quality, self._energy_spent, self._critic_gain)

    # -- Read-only accessors ----------------------------------------

    @property
    def critic_gain(self) -> float:
        """Current critic gain (read-only)."""
        return self._critic_gain

    @property
    def energy_spent(self) -> float:
        """Energy consumed so far in the current cycle."""
        return self._energy_spent

    @property
    def cycle(self) -> int:
        """Current cycle ordinal."""
        return self._cycle


# ------------------------------------------------------------------
# Integration with CoherenceStateSpace
# ------------------------------------------------------------------


def simulate_with_oeb(
    model: CoherenceStateSpace,
    oeb_controller: OEBController,
    initial_state: CoherenceState,
    n_steps: int,
    rng: np.random.Generator | None = None,
) -> tuple[FloatArray, list[ObjectionBudget]]:
    """Coupled simulation: OEB controller drives objection energy in the
    state-space model.

    At each timestep:
    1. The controller's ``critic_gain`` is used as the ``u_E`` input to the
       state-space model (higher gain → more objection energy injected).
    2. The resulting ``E_obj`` from the state is used to derive synthetic
       ``hallucination_rate`` and ``false_reject_rate`` for the next PID
       step (simple heuristic: halluc_rate ~ 1/(1 + E_obj), false_rej ~
       sigmoid(E_obj - threshold)).

    Returns
    -------
    trajectory : ndarray of shape (n_steps + 1, 4)
        State trajectory including the initial state.
    budgets : list[ObjectionBudget]
        One budget snapshot per step (length ``n_steps``).
    """
    if n_steps < 0:
        raise ValueError("n_steps must be non-negative")

    trajectory = np.empty((n_steps + 1, 4), dtype=np.float64)
    trajectory[0] = initial_state.as_vector()
    budgets: list[ObjectionBudget] = []

    state = initial_state
    for t in range(n_steps):
        # Use critic_gain as u_E input; u_S = 0
        u_e = oeb_controller.critic_gain
        state = model.step(state, (0.0, u_e), rng)
        trajectory[t + 1] = state.as_vector()

        # Derive synthetic rates from state for next PID step
        e_obj = state.E_obj
        halluc_rate = float(1.0 / (1.0 + e_obj))
        # False-reject rate rises when E_obj is very high
        false_rej_rate = float(1.0 / (1.0 + np.exp(-(e_obj - 2.0))))

        budget = oeb_controller.step(halluc_rate, false_rej_rate)
        budgets.append(budget)

    return trajectory, budgets
