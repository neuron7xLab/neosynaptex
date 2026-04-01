"""NCE — Neurosymbolic Cognitive Engine: reasoning, calibration, abduction."""

from neuron7x_agents.cognitive.engine import CognitiveEngine
from neuron7x_agents.cognitive.strategies import (
    AbductiveInference,
    EpistemicForaging,
    PredictiveCoding,
    ReductioAdAbsurdum,
)

__all__ = [
    "AbductiveInference",
    "CognitiveEngine",
    "EpistemicForaging",
    "PredictiveCoding",
    "ReductioAdAbsurdum",
]
