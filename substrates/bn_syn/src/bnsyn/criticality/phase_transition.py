"""Phase transition detection for criticality analysis.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements phase transition detector for tracking critical state transitions.

References
----------
docs/SPEC.md#P0-4
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class CriticalPhase(Enum):
    """Critical phase enumeration.

    Attributes
    ----------
    SUBCRITICAL : int
        Below critical point (sigma < 0.95)
    CRITICAL : int
        At critical point (0.95 <= sigma <= 1.05)
    SUPERCRITICAL : int
        Above critical point (sigma > 1.05)
    UNKNOWN : int
        Phase not yet determined
    """

    SUBCRITICAL = 0
    CRITICAL = 1
    SUPERCRITICAL = 2
    UNKNOWN = 3


@dataclass(frozen=True)
class PhaseTransition:
    """Record of a phase transition event.

    Parameters
    ----------
    step : int
        Simulation step when transition occurred.
    from_phase : CriticalPhase
        Phase before transition.
    to_phase : CriticalPhase
        Phase after transition.
    sigma_before : float
        Sigma value before transition.
    sigma_after : float
        Sigma value after transition.
    sharpness : float
        Transition sharpness (absolute difference in sigma).
    """

    step: int
    from_phase: CriticalPhase
    to_phase: CriticalPhase
    sigma_before: float
    sigma_after: float
    sharpness: float


class PhaseTransitionDetector:
    """Detector for phase transitions in criticality.

    Parameters
    ----------
    subcritical_threshold : float, optional
        Upper bound for subcritical phase (default: 0.95).
    supercritical_threshold : float, optional
        Lower bound for supercritical phase (default: 1.05).
    history_size : int, optional
        Maximum history size for sigma tracking (default: 200).

    Notes
    -----
    Tracks sigma history in a deque with maximum size to detect transitions.

    References
    ----------
    docs/SPEC.md#P0-4
    """

    def __init__(
        self,
        subcritical_threshold: float = 0.95,
        supercritical_threshold: float = 1.05,
        history_size: int = 200,
    ):
        """Initialize transition detector thresholds and bounded histories.

        Parameters
        ----------
        subcritical_threshold : float, optional
            Upper sigma boundary for subcritical classification.
        supercritical_threshold : float, optional
            Lower sigma boundary for supercritical classification.
        history_size : int, optional
            Maximum number of sigma/phase observations retained.

        Raises
        ------
        ValueError
            If thresholds are unordered or ``history_size`` is non-positive.

        Notes
        -----
        Maintains fixed-size deques for deterministic memory bounds and
        transition sharpness calculations over recent observations.
        """
        if subcritical_threshold >= supercritical_threshold:
            raise ValueError("subcritical_threshold must be less than supercritical_threshold")
        if history_size <= 0:
            raise ValueError("history_size must be positive")

        self.subcritical_threshold = subcritical_threshold
        self.supercritical_threshold = supercritical_threshold
        self.history_size = history_size

        self._sigma_history: deque[tuple[int, float]] = deque(maxlen=history_size)
        self._phase_history: deque[tuple[int, CriticalPhase]] = deque(maxlen=history_size)
        self._current_phase: CriticalPhase = CriticalPhase.UNKNOWN
        self._transitions: list[PhaseTransition] = []
        self._transition_callbacks: list[Callable[[PhaseTransition], None]] = []
        self._step_entered_phase: int = 0

    def _classify_phase(self, sigma: float) -> CriticalPhase:
        """Classify sigma value into a phase.

        Parameters
        ----------
        sigma : float
            Sigma value to classify.

        Returns
        -------
        CriticalPhase
            Classified phase.
        """
        if sigma < self.subcritical_threshold:
            return CriticalPhase.SUBCRITICAL
        elif sigma > self.supercritical_threshold:
            return CriticalPhase.SUPERCRITICAL
        else:
            return CriticalPhase.CRITICAL

    def observe(self, sigma: float, step: int) -> CriticalPhase | None:
        """Observe a sigma value and detect transitions.

        Parameters
        ----------
        sigma : float
            Current sigma value.
        step : int
            Current simulation step.

        Returns
        -------
        CriticalPhase | None
            New phase if transition occurred, None otherwise.

        Notes
        -----
        Updates internal state and triggers callbacks on transitions.
        """
        # classify current sigma
        new_phase = self._classify_phase(sigma)

        # record history
        self._sigma_history.append((step, sigma))
        self._phase_history.append((step, new_phase))

        # detect transition
        if new_phase != self._current_phase and self._current_phase != CriticalPhase.UNKNOWN:
            # get previous sigma
            sigma_before = self._sigma_history[-2][1] if len(self._sigma_history) >= 2 else sigma
            sharpness = abs(sigma - sigma_before)

            transition = PhaseTransition(
                step=step,
                from_phase=self._current_phase,
                to_phase=new_phase,
                sigma_before=sigma_before,
                sigma_after=sigma,
                sharpness=sharpness,
            )
            self._transitions.append(transition)

            # trigger callbacks
            for callback in self._transition_callbacks:
                callback(transition)

            # update current phase
            self._current_phase = new_phase
            self._step_entered_phase = step

            return new_phase

        # initialize or update current phase
        if self._current_phase == CriticalPhase.UNKNOWN:
            self._current_phase = new_phase
            self._step_entered_phase = step

        return None

    def on_transition(self, callback: Callable[[PhaseTransition], None]) -> None:
        """Register a callback for phase transitions.

        Parameters
        ----------
        callback : Callable[[PhaseTransition], None]
            Callback function receiving PhaseTransition.
        """
        self._transition_callbacks.append(callback)

    def current_phase(self) -> CriticalPhase:
        """Return current critical phase.

        Returns
        -------
        CriticalPhase
            Current phase.
        """
        return self._current_phase

    def sigma_derivative(self) -> float | None:
        """Compute derivative of sigma over recent history.

        Returns
        -------
        float | None
            Derivative estimate (sigma change per step) or None if insufficient history.

        Notes
        -----
        Uses last 10 observations if available.
        """
        if len(self._sigma_history) < 2:
            return None

        # use last 10 observations for derivative estimate
        n = min(10, len(self._sigma_history))
        recent = list(self._sigma_history)[-n:]
        steps = [s for s, _ in recent]
        sigmas = [sig for _, sig in recent]

        # simple linear fit
        if len(steps) < 2:
            return None

        delta_step = steps[-1] - steps[0]
        delta_sigma = sigmas[-1] - sigmas[0]

        if delta_step == 0:
            return 0.0

        return delta_sigma / delta_step

    def time_in_phase(self, step: int) -> int:
        """Return time spent in current phase.

        Parameters
        ----------
        step : int
            Current simulation step.

        Returns
        -------
        int
            Number of steps in current phase.
        """
        return step - self._step_entered_phase

    def get_transitions(self) -> list[PhaseTransition]:
        """Return list of detected transitions.

        Returns
        -------
        list[PhaseTransition]
            List of all detected transitions.
        """
        return self._transitions.copy()

    def get_sigma_history(self) -> list[tuple[int, float]]:
        """Return sigma history.

        Returns
        -------
        list[tuple[int, float]]
            List of (step, sigma) tuples.
        """
        return list(self._sigma_history)

    def get_phase_history(self) -> list[tuple[int, CriticalPhase]]:
        """Return phase history.

        Returns
        -------
        list[tuple[int, CriticalPhase]]
            List of (step, phase) tuples.
        """
        return list(self._phase_history)
