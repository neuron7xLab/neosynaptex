"""
DNCA — Distributed Neuromodulatory Cognitive Architecture
==========================================================

Cognition is the regulated succession of metastable dominant regimes
over a shared predictive state. Intelligence is the system's capacity
to sustain adaptive transitions between regimes under competition
without collapse or rigidity.

Six neuromodulatory operators:
    DA  — Dopamine:       significance, salience, RPE
    ACh — Acetylcholine:  precision, attention, persistence
    NE  — Norepinephrine: adaptive gain, mode switching, reset
    5HT — Serotonin:      patience, inhibition, temporal discount
    GABA:                 competition normalization
    Glu — Glutamate:      plasticity, error amplification

Usage:
    >>> from neuron7x_agents.dnca import DNCA
    >>> system = DNCA(state_dim=64)
    >>> output = system.step(sensory_input, reward=0.5)

Yaroslav Vasylenko / neuron7xLab / 2026
"""

__version__ = "1.0.0"

from neuron7x_agents.dnca.orchestrator import DNCA, DNCStepOutput
from neuron7x_agents.dnca.core.sps import SharedPredictiveState
from neuron7x_agents.dnca.core.dac import DominantAcceptorCycle, DACOutput
from neuron7x_agents.dnca.core.nmo import NeuromodulatoryOperator
from neuron7x_agents.dnca.core.types import (
    NMOType,
    RegimePhase,
    RegimeTransitionEvent,
    DNCAAudit,
)
from neuron7x_agents.dnca.competition.lotka_volterra import LotkaVolterraField
from neuron7x_agents.dnca.competition.kuramoto import KuramotoCoupling
from neuron7x_agents.dnca.competition.metastability import MetastabilityEngine
from neuron7x_agents.dnca.regime import DominantRegime, RegimeManager
from neuron7x_agents.dnca.neuromodulators import (
    DopamineOperator,
    AcetylcholineOperator,
    NorepinephrineOperator,
    SerotoninOperator,
    GABAOperator,
    GlutamateOperator,
)

__all__ = [
    "DNCA",
    "DNCStepOutput",
    "SharedPredictiveState",
    "DominantAcceptorCycle",
    "NeuromodulatoryOperator",
    "NMOType",
    "RegimePhase",
    "RegimeTransitionEvent",
    "LotkaVolterraField",
    "KuramotoCoupling",
    "MetastabilityEngine",
    "DominantRegime",
    "RegimeManager",
    "DopamineOperator",
    "AcetylcholineOperator",
    "NorepinephrineOperator",
    "SerotoninOperator",
    "GABAOperator",
    "GlutamateOperator",
]
