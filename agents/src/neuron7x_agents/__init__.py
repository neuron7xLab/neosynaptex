"""
neuron7x-agents · Distributed Neuromodulatory Cognitive Architecture
=====================================================================

Five pillars of cognitive agency:

    primitives/     Shared cognitive building blocks (CorticalColumn, evidence)
    cognitive/      NCE: reasoning, calibration, abductive inference
    regulation/     SERO: hormonal stress regulation, homeostasis
    verification/   Kriterion: fail-closed epistemic verification
    ensemble/       NCE-E: neuromodulatory cognitive ensemble (Dominant-Acceptor)
    agents/         Composed agent blueprints

The ensemble module implements the core architecture: eight autonomous
regulatory cycles (salience, focus, activation, inhibition, switching,
memory, consolidation, adaptation) compete for a shared cognitive
workspace through Ukhtomsky-style monopolistic dynamics. Each cycle
runs its own Dominant-Acceptor loop with a characteristic neuromodulatory
profile (DA/NE/ACh/5-HT). Cognition IS the interaction pattern.

Author: Yaroslav Vasylenko · neuron7xLab · Ukraine · 2026
"""

from __future__ import annotations

__version__ = "0.2.0"
__author__ = "Yaroslav Vasylenko"

from neuron7x_agents.agents.hybrid import HybridAgent
from neuron7x_agents.cognitive.engine import CognitiveEngine
from neuron7x_agents.primitives.column import CorticalColumn
from neuron7x_agents.regulation.hvr import HormonalRegulator
from neuron7x_agents.verification.gate import EpistemicGate
from neuron7x_agents.ensemble.orchestrator import NeuromodEnsemble
from neuron7x_agents.ensemble.cycle import RegulatoryCycle, RegulatoryFunction
from neuron7x_agents.ensemble.bridge import EnsembleSEROBridge

__all__ = [
    "CognitiveEngine",
    "CorticalColumn",
    "EpistemicGate",
    "HormonalRegulator",
    "HybridAgent",
    "NeuromodEnsemble",
    "RegulatoryCycle",
    "RegulatoryFunction",
    "EnsembleSEROBridge",
    "__version__",
]
