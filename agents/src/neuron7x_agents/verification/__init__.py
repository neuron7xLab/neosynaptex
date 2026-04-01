"""Kriterion — fail-closed epistemic verification."""

from neuron7x_agents.verification.anti_gaming import AntiGamingDetector
from neuron7x_agents.verification.gate import EpistemicGate, GateVerdict

__all__ = [
    "AntiGamingDetector",
    "EpistemicGate",
    "GateVerdict",
]
