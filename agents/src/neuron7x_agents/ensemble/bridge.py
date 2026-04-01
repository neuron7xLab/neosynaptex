"""
Bridge — connects NeuromodEnsemble with existing neuron7x-agents subsystems.

Maps:
  SERO HormonalRegulator → ensemble neuromodulator dynamics
  NCE CognitiveEngine → ensemble reasoning integration
  Kriterion EpistemicGate → ensemble output verification

This bridge makes the ensemble a first-class citizen in the
neuron7x-agents ecosystem, not a parallel system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch

from neuron7x_agents.ensemble.cycle import RegulatoryFunction
from neuron7x_agents.ensemble.orchestrator import EnsembleStepOutput, NeuromodEnsemble
from neuron7x_agents.ensemble.workspace import WorkspaceState
from neuron7x_agents.regulation.hvr import HormonalRegulator, HVRConfig, SeverityWeight, StressState


@dataclass(slots=True)
class BridgedOutput:
    """Combined output from ensemble + SERO regulation."""
    ensemble: EnsembleStepOutput
    stress: StressState
    throughput: float
    is_stressed: bool


class EnsembleSEROBridge:
    """
    Maps ensemble dynamics → SERO stress channels.

    The key insight: each regulatory cycle's mismatch signal IS a
    stress channel. High mismatch in the SALIENCE cycle = salience
    stress. High mismatch in MEMORY = memory stress. Etc.

    SERO then computes the overall throughput from these channels,
    which feeds back to the ensemble as a global gain modulator.
    """

    def __init__(
        self,
        ensemble: NeuromodEnsemble,
        hvr_config: Optional[HVRConfig] = None,
    ):
        self.ensemble = ensemble
        self.hvr = HormonalRegulator(hvr_config or HVRConfig())

        # Map regulatory functions to SERO severity weights
        self._severity_map = {
            RegulatoryFunction.SALIENCE: 0.8,
            RegulatoryFunction.FOCUS: 0.6,
            RegulatoryFunction.ACTIVATION: 0.7,
            RegulatoryFunction.INHIBITION: 0.5,
            RegulatoryFunction.SWITCHING: 0.9,  # high cost to switch
            RegulatoryFunction.MEMORY: 0.6,
            RegulatoryFunction.CONSOLIDATION: 0.4,
            RegulatoryFunction.ADAPTATION: 0.7,
        }

    def step(
        self,
        sensory_input: torch.Tensor,
        goal: Optional[torch.Tensor] = None,
        reward: float = 0.0,
    ) -> BridgedOutput:
        """Run ensemble step + SERO regulation."""
        # 1. Ensemble step
        ens_out = self.ensemble.step(sensory_input, goal, reward)

        # 2. Build SERO stress channels from ensemble cycle mismatches
        channels: List[SeverityWeight] = []
        for func in RegulatoryFunction:
            name = func.name
            if name in self.ensemble.cycles:
                cycle = self.ensemble.cycles[name]
                # Mismatch history as stress signal
                recent_mismatch = (
                    sum(cycle.mismatch_history[-5:]) / max(1, min(5, len(cycle.mismatch_history)))
                    if cycle.mismatch_history else 0.0
                )
                channels.append(SeverityWeight(
                    name=name,
                    severity=self._severity_map.get(func, 0.5),
                    current_value=min(1.0, recent_mismatch),
                ))

        # 3. SERO tick
        stress = self.hvr.tick(channels)

        return BridgedOutput(
            ensemble=ens_out,
            stress=stress,
            throughput=stress.throughput,
            is_stressed=stress.is_stressed,
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "ensemble": self.ensemble.get_diagnostics(),
            "sero": {
                "throughput": self.hvr._last_state.throughput if hasattr(self.hvr, '_last_state') else 1.0,
                "safety_invariant": self.hvr.safety_invariant_holds(),
            },
        }

    def reset(self) -> None:
        self.ensemble.reset()
        self.hvr.reset()
