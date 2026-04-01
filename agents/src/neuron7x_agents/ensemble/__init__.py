"""
Neuromodulatory Cognitive Ensemble (NCE-E)
==========================================

Distributed cognitive architecture where agency emerges from
competitive-cooperative dynamics of autonomous regulatory cycles.

Each cycle is NOT a role or persona — it is a regulatory PRINCIPLE:
salience, focus, activation, inhibition, switching, memory,
consolidation, adaptation. Each runs its own Dominant-Acceptor loop
with a characteristic neuromodulatory profile (DA/NE/ACh/5-HT).

Cognition IS the interaction pattern of these cycles.
"""

from neuron7x_agents.ensemble.cycle import (
    CANONICAL_PROFILES,
    RegulatoryCycle,
    RegulatoryFunction,
    RegulatoryProfile,
)
from neuron7x_agents.ensemble.workspace import CognitiveWorkspace, WorkspaceState
from neuron7x_agents.ensemble.orchestrator import EnsembleStepOutput, NeuromodEnsemble
from neuron7x_agents.ensemble.bridge import EnsembleSEROBridge, BridgedOutput

__all__ = [
    "CANONICAL_PROFILES",
    "RegulatoryCycle",
    "RegulatoryFunction",
    "RegulatoryProfile",
    "CognitiveWorkspace",
    "WorkspaceState",
    "EnsembleStepOutput",
    "NeuromodEnsemble",
    "EnsembleSEROBridge",
    "BridgedOutput",
]
