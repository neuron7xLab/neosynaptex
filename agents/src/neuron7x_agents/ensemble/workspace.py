"""
CognitiveWorkspace — the shared arena where regulatory cycles compete.

Inspired by Baars' Global Workspace Theory (1988) but implemented as
a competitive Ukhtomsky field rather than a broadcast mechanism.

The workspace holds:
- Current cognitive state (shared across all cycles)
- Winning cycle's output (the current "dominant" regulation mode)
- History of transitions (for replay and consolidation)
- Oscillatory phase (theta-gamma for temporal binding)

Cycles do NOT communicate directly. They interact ONLY through
the workspace state — reading it, proposing actions to it, and
competing for write access.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import torch


@dataclass(slots=True)
class WorkspaceState:
    """
    Snapshot of the cognitive workspace at one moment.

    This is what all regulatory cycles can READ.
    Only the WINNING cycle can WRITE (propose action).
    """
    # Current state
    sensory_input: torch.Tensor
    encoded_state: torch.Tensor
    goal: Optional[torch.Tensor] = None

    # Winning cycle info
    active_cycle: Optional[str] = None    # RegulatoryFunction name
    active_strength: float = 0.0
    active_age: int = 0

    # Acceptor signals (from winning cycle)
    mismatch: float = 0.0
    satiation: float = 0.0
    orienting: float = 0.0

    # Oscillatory phase
    theta_phase: float = 0.0
    pac_strength: float = 0.0

    # Action output
    proposed_action: Optional[torch.Tensor] = None

    # External signals
    reward: float = 0.0
    timestamp: int = 0


@dataclass
class TransitionLog:
    """One workspace transition for history/replay."""
    state: WorkspaceState
    action: Optional[torch.Tensor]
    next_state: Optional[WorkspaceState] = None
    reward: float = 0.0
    winning_cycle: Optional[str] = None


class CognitiveWorkspace:
    """
    The arena where regulatory cycles compete and cooperate.

    Key properties:
    1. Single writer: only the winning cycle writes to the workspace
    2. All readers: every cycle can read the current state
    3. History: maintains a bounded log of transitions
    4. No direct cycle-to-cycle communication

    The workspace does NOT decide who wins. That's the orchestrator's job.
    The workspace just holds state and enforces access patterns.
    """

    def __init__(
        self,
        state_dim: int = 64,
        history_capacity: int = 512,
    ):
        self.state_dim = state_dim
        self._current: Optional[WorkspaceState] = None
        self._history: deque[TransitionLog] = deque(maxlen=history_capacity)
        self._tick = 0

    @property
    def current(self) -> Optional[WorkspaceState]:
        return self._current

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def history(self) -> List[TransitionLog]:
        return list(self._history)

    def receive_input(
        self,
        sensory: torch.Tensor,
        goal: Optional[torch.Tensor] = None,
        reward: float = 0.0,
    ) -> WorkspaceState:
        """
        New sensory input arrives. Create a fresh workspace state.
        Previous state becomes history.
        """
        self._tick += 1

        new_state = WorkspaceState(
            sensory_input=sensory.detach().clone(),
            encoded_state=sensory.detach().clone(),  # will be overwritten by winner
            goal=goal.detach().clone() if goal is not None else None,
            reward=reward,
            timestamp=self._tick,
        )

        # Log transition from previous state
        if self._current is not None:
            self._history.append(TransitionLog(
                state=self._current,
                action=self._current.proposed_action,
                next_state=new_state,
                reward=reward,
                winning_cycle=self._current.active_cycle,
            ))

        self._current = new_state
        return new_state

    def write(
        self,
        cycle_name: str,
        encoded_state: torch.Tensor,
        proposed_action: torch.Tensor,
        strength: float,
        age: int,
        mismatch: float,
        satiation: float,
        orienting: float,
        theta_phase: float = 0.0,
        pac_strength: float = 0.0,
    ) -> None:
        """
        Winning cycle writes its output to the workspace.
        Only the orchestrator should call this after competition.
        """
        if self._current is None:
            return

        self._current.encoded_state = encoded_state.detach().clone()
        self._current.proposed_action = proposed_action.detach().clone()
        self._current.active_cycle = cycle_name
        self._current.active_strength = strength
        self._current.active_age = age
        self._current.mismatch = mismatch
        self._current.satiation = satiation
        self._current.orienting = orienting
        self._current.theta_phase = theta_phase
        self._current.pac_strength = pac_strength

    def get_recent_rewards(self, n: int = 10) -> List[float]:
        """Last N rewards from history."""
        recent = list(self._history)[-n:]
        return [t.reward for t in recent]

    def get_cycle_durations(self) -> Dict[str, int]:
        """How long each cycle held dominance."""
        durations: Dict[str, int] = {}
        for t in self._history:
            if t.winning_cycle:
                durations[t.winning_cycle] = durations.get(t.winning_cycle, 0) + 1
        return durations

    def reset(self) -> None:
        self._current = None
        self._history.clear()
        self._tick = 0
