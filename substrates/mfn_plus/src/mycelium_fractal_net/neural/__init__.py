"""Neural spiking substrate for MyceliumFractalNet.

Adapted from BN-Syn (phase-controlled emergent dynamics).
Provides AdEx spiking network as an alternative substrate to R-D simulation,
with full MFN analytics pipeline compatibility.

Public surface (11 symbols, stable contract):
    NeuralExtension, NeuralConfig, NeuralReport
    AdExNeuron, ConductanceSynapse, STDPRule
    CriticalityTracker, EmergenceDetector
    SpikeFieldConverter
    simulate_neural, diagnose_neural

Hard dependencies: numpy (always), scipy (branching ratio fitting)
Import budget: neural/ must not import from integration/, api/, cli/

Computational contracts (enforced by benchmark gates):
    AdExNeuron.step() @ N=128:  < 1ms
    Network.step()    @ N=128:  < 5ms
    SpikeFieldConverter @ N=128, T=2000: < 50ms

Ref: Brette & Gerstner (2005) J. Comput. Neurosci. 18:1467
     Hoel, Albantakis & Tononi (2013) PNAS 110:19790
"""

from .adex import AdExNeuron, AdExParams, AdExState
from .conductance import ConductanceSynapse, SynapseParams
from .converter import SpikeFieldConverter, SpikeRaster
from .criticality import CriticalityParams, CriticalityReport, CriticalityTracker
from .emergence import AttractorState, EmergenceDetector, EmergencePhase
from .extension import NeuralConfig, NeuralExtension, NeuralReport
from .network import NetworkParams, SpikeNetwork
from .stdp import PlasticityParams, STDPRule

__all__ = [
    # Core types
    "AdExNeuron",
    "AdExParams",
    "AdExState",
    "AttractorState",
    "ConductanceSynapse",
    "CriticalityParams",
    "CriticalityReport",
    # Analysis
    "CriticalityTracker",
    "EmergenceDetector",
    "EmergencePhase",
    "NetworkParams",
    "NeuralConfig",
    "NeuralExtension",
    "NeuralReport",
    "PlasticityParams",
    "STDPRule",
    # Bridge to MFN
    "SpikeFieldConverter",
    # Network
    "SpikeNetwork",
    "SpikeRaster",
    "SynapseParams",
]
