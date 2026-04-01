"""
NeuromodEnsemble — the distributed neuromodulatory cognitive architecture.

This is NOT an orchestrator in the classical multi-agent sense.
There is no central planner, no task router, no role assignment.

This is a COMPETITIVE FIELD where regulatory cycles fight for
dominance through Ukhtomsky dynamics:

1. All cycles evaluate the current workspace state
2. Each computes its strength (how relevant it is right now)
3. Winner-take-all: strongest cycle captures the workspace
4. Winner runs its D-A loop: encode → predict → act → compare
5. When winner saturates → next strongest takes over
6. Neuromodulators gate the competition dynamics

Cognition = the sequence of winning cycles over time.
Agency = emergent property of this competitive dynamics.

No roles. No personas. No orchestration. Just physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from neuron7x_agents.ensemble.cycle import (
    CANONICAL_PROFILES,
    RegulatoryCycle,
    RegulatoryFunction,
    RegulatoryProfile,
)
from neuron7x_agents.ensemble.workspace import CognitiveWorkspace, WorkspaceState


@dataclass(slots=True)
class EnsembleStepOutput:
    """Output of one ensemble cycle."""
    workspace: WorkspaceState
    winning_cycle: str
    winning_strength: float
    all_strengths: Dict[str, float]
    action: torch.Tensor
    mismatch: float
    satiation: float
    orienting: float
    cycle_number: int


class NeuromodEnsemble(nn.Module):
    """
    Distributed Neuromodulatory Cognitive Ensemble.

    Eight regulatory cycles with canonical neuromodulatory profiles
    compete for a shared cognitive workspace. The winner at each
    timestep dictates system behavior. Transitions between winners
    create the temporal structure of cognition.

    This mirrors how the brain works:
    - Dopaminergic circuits handle salience/reward
    - Noradrenergic circuits handle arousal/attention
    - Cholinergic circuits handle memory encoding
    - Serotonergic circuits handle behavioral inhibition
    - They all share the same cortical workspace
    - Only one mode dominates at a time (Ukhtomsky)
    """

    def __init__(
        self,
        state_dim: int = 64,
        hidden_dim: int = 128,
        profiles: Optional[Dict[RegulatoryFunction, RegulatoryProfile]] = None,
        lateral_inhibition: float = 0.2,
    ):
        super().__init__()
        self.state_dim = state_dim
        self.lateral_inhibition = lateral_inhibition

        # Create cycles with canonical (or custom) profiles
        profiles = profiles or CANONICAL_PROFILES
        self.cycles = nn.ModuleDict()
        for func, profile in profiles.items():
            self.cycles[func.name] = RegulatoryCycle(
                profile=profile,
                state_dim=state_dim,
                hidden_dim=hidden_dim,
            )

        # Workspace
        self.workspace = CognitiveWorkspace(state_dim=state_dim)

        # Competition state
        self._current_winner: Optional[str] = None
        self._winner_age: int = 0
        self._cycle_count: int = 0

    def _compete(self, state: torch.Tensor) -> Tuple[str, float, Dict[str, float]]:
        """
        Winner-take-all competition. NOT softmax.

        Each cycle computes its strength. The strongest wins.
        Losers are suppressed proportionally (lateral inhibition).
        The previous winner gets a persistence bonus (inertia).
        """
        strengths: Dict[str, float] = {}
        for name, cycle in self.cycles.items():
            raw = cycle.compute_strength(state)
            # Inertia bonus: current winner persists
            if name == self._current_winner:
                raw += 0.1 * min(self._winner_age / 10.0, 1.0)
            # Satiation penalty: saturated cycles yield
            if cycle.is_saturated:
                raw *= 0.1
            strengths[name] = raw

        if not strengths:
            return "NONE", 0.0, strengths

        # Hard WTA
        winner_name = max(strengths, key=strengths.get)  # type: ignore
        winner_strength = strengths[winner_name]

        # Lateral inhibition: suppress losers
        for name in strengths:
            if name != winner_name:
                strengths[name] = max(0.0, strengths[name] - self.lateral_inhibition * winner_strength)

        # Track winner continuity
        if winner_name == self._current_winner:
            self._winner_age += 1
        else:
            # New winner: reset all related state
            if self._current_winner is not None:
                self.cycles[self._current_winner].reset()
            self._winner_age = 0
            self._current_winner = winner_name

        return winner_name, winner_strength, strengths

    def step(
        self,
        sensory_input: torch.Tensor,
        goal: Optional[torch.Tensor] = None,
        reward: float = 0.0,
    ) -> EnsembleStepOutput:
        """
        One cycle of the ensemble:

        1. Workspace receives new input
        2. All cycles evaluate strength (parallel)
        3. WTA competition selects winner
        4. Winner runs full D-A loop
        5. Winner writes to workspace
        """
        self._cycle_count += 1

        # 1. Workspace receives input
        ws = self.workspace.receive_input(sensory_input, goal, reward)

        # 2-3. Competition
        winner_name, winner_strength, all_strengths = self._compete(sensory_input)
        winner: RegulatoryCycle = self.cycles[winner_name]

        # 4. Winner runs its D-A loop
        encoded = winner.encode(sensory_input)
        prediction = winner.predict(encoded)
        action = winner.propose_action(encoded)

        # Compare with previous prediction (if available)
        comparison = winner.compare(prediction, encoded)

        # 5. Write to workspace
        self.workspace.write(
            cycle_name=winner_name,
            encoded_state=encoded,
            proposed_action=action,
            strength=winner_strength,
            age=comparison["age"],
            mismatch=comparison["mismatch"],
            satiation=comparison["satiation"],
            orienting=comparison["orienting"],
        )

        return EnsembleStepOutput(
            workspace=ws,
            winning_cycle=winner_name,
            winning_strength=winner_strength,
            all_strengths=all_strengths,
            action=action.detach(),
            mismatch=comparison["mismatch"],
            satiation=comparison["satiation"],
            orienting=comparison["orienting"],
            cycle_number=self._cycle_count,
        )

    def run(
        self,
        inputs: List[torch.Tensor],
        goals: Optional[List[torch.Tensor]] = None,
        rewards: Optional[List[float]] = None,
    ) -> List[EnsembleStepOutput]:
        """Run ensemble over a sequence of inputs."""
        results = []
        for i, inp in enumerate(inputs):
            goal = goals[i] if goals else None
            reward = rewards[i] if rewards else 0.0
            results.append(self.step(inp, goal, reward))
        return results

    def get_diagnostics(self) -> Dict[str, Any]:
        """Diagnostic state of the ensemble."""
        return {
            "cycle_count": self._cycle_count,
            "current_winner": self._current_winner,
            "winner_age": self._winner_age,
            "cycle_durations": self.workspace.get_cycle_durations(),
            "workspace_history_size": len(self.workspace.history),
            "cycle_satiations": {
                name: cycle._satiation
                for name, cycle in self.cycles.items()
            },
        }

    def reset(self) -> None:
        """Reset ensemble to initial state."""
        for cycle in self.cycles.values():
            cycle.reset()
        self.workspace.reset()
        self._current_winner = None
        self._winner_age = 0
        self._cycle_count = 0
