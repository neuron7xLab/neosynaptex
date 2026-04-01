"""
DominantRegime lifecycle + RegimeManager.

INV-7: Every regime transition must emit a RegimeTransitionEvent.
Transitions that are not logged do not count as transitions.

Lifecycle: FORMING → ACTIVE → SATURATING → DISSOLVING → COLLAPSED
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import torch

from neuron7x_agents.dnca.core.types import (
    CAPTURE_THRESHOLD,
    COMPETITION_RATIO,
    DOMINANCE_THRESHOLD,
    MAX_REGIME_DURATION,
    MISMATCH_COLLAPSE,
    MIN_REGIME_DURATION,
    SATIATION_THRESHOLD,
    RegimePhase,
    RegimeTransitionEvent,
)


@dataclass
class DominantRegime:
    """A transient configuration where NMOs form a processing coalition."""
    regime_id: int
    dominant_nmo: str
    phase: RegimePhase = RegimePhase.FORMING
    formation_step: int = 0
    age: int = 0
    coherence_at_formation: float = 0.0
    energy_profile: Optional[torch.Tensor] = None
    goal: Optional[torch.Tensor] = None
    satiation: float = 0.0
    mismatch_integral: float = 0.0


class RegimeManager:
    """
    Manages regime lifecycle and emits transition events.

    INV-7: every transition emits RegimeTransitionEvent.
    INV-4: no regime persists beyond MAX_REGIME_DURATION.
    """

    def __init__(self, event_log_capacity: int = 1000):
        self._current: Optional[DominantRegime] = None
        self._next_id = 0
        self._events: deque[RegimeTransitionEvent] = deque(maxlen=event_log_capacity)
        self._step: int = 0

    @property
    def current(self) -> Optional[DominantRegime]:
        return self._current

    @property
    def events(self) -> List[RegimeTransitionEvent]:
        return list(self._events)

    @property
    def transition_count(self) -> int:
        return len(self._events)

    def update(
        self,
        dominant_nmo: str,
        dominant_activity: float,
        dominant_satiation: float,
        dominant_mismatch: float,
        coherence: float,
        ne_reset: bool,
        challenger_activity: float,
        goal: Optional[torch.Tensor] = None,
    ) -> Optional[RegimeTransitionEvent]:
        """
        Update regime lifecycle. Returns transition event if one occurred.
        """
        self._step += 1
        event: Optional[RegimeTransitionEvent] = None

        # --- Check for regime termination ---
        if self._current is not None:
            self._current.age += 1
            self._current.satiation = dominant_satiation
            self._current.mismatch_integral += dominant_mismatch

            trigger: Optional[str] = None

            # T1: Satiation — goal achieved
            if dominant_satiation >= SATIATION_THRESHOLD:
                trigger = "satiation"

            # T2: Mismatch collapse — prediction systematically fails
            elif self._current.mismatch_integral > MISMATCH_COLLAPSE and self._current.age > 200:
                trigger = "mismatch_collapse"

            # T3: NE reset — context change detected
            elif ne_reset:
                trigger = "ne_reset"

            # T4: Max duration — forced transition (INV-4)
            elif self._current.age >= MAX_REGIME_DURATION:
                trigger = "max_duration"

            # T5: Overthrow — challenger is close to dominant
            elif (challenger_activity > dominant_activity * COMPETITION_RATIO
                  and self._current.age >= MIN_REGIME_DURATION):
                trigger = "overthrow"

            if trigger is not None:
                event = RegimeTransitionEvent(
                    step=self._step,
                    from_regime_id=self._current.regime_id,
                    to_regime_id=self._next_id,
                    from_nmo=self._current.dominant_nmo,
                    to_nmo=dominant_nmo if trigger != "satiation" else None,
                    trigger=trigger,
                    coherence_at_transition=coherence,
                    from_duration=self._current.age,
                )
                self._events.append(event)

                # Collapse current regime
                self._current.phase = RegimePhase.COLLAPSED
                self._current = None

        # --- Check for new regime formation ---
        if self._current is None and dominant_activity >= CAPTURE_THRESHOLD:
            self._current = DominantRegime(
                regime_id=self._next_id,
                dominant_nmo=dominant_nmo,
                phase=RegimePhase.FORMING,
                formation_step=self._step,
                coherence_at_formation=coherence,
                goal=goal.clone() if goal is not None else None,
            )
            self._next_id += 1

        # --- Phase transitions within current regime ---
        if self._current is not None:
            if dominant_activity >= DOMINANCE_THRESHOLD and self._current.phase == RegimePhase.FORMING:
                self._current.phase = RegimePhase.ACTIVE
            elif self._current.satiation > SATIATION_THRESHOLD * 0.7 and self._current.phase == RegimePhase.ACTIVE:
                self._current.phase = RegimePhase.SATURATING
            elif self._current.phase == RegimePhase.SATURATING and coherence < 0.3:
                self._current.phase = RegimePhase.DISSOLVING

        return event

    def get_regime_durations(self) -> List[int]:
        """Durations of all completed regimes."""
        return [e.from_duration for e in self._events]

    def get_regime_sequence(self) -> List[str]:
        """Sequence of dominant NMO names."""
        return [e.from_nmo for e in self._events if e.from_nmo is not None]

    def reset(self) -> None:
        self._current = None
        self._next_id = 0
        self._events.clear()
        self._step = 0
