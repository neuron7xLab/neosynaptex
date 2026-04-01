"""
Neuro-AI contract layer adapters.

This package adds a thin compatibility layer that formalizes the computational
contracts of biomimetic modules (synaptic memory, cognitive rhythm, and
synergy learning) while keeping the default behavior untouched.

The adapters are opt-in: when disabled they delegate directly to the existing
implementations, ensuring no breaking changes to public APIs.
"""

from .adapters import (
    NeuroAIStepMetrics,
    PredictionErrorAdapter,
    PredictionErrorMetrics,
    RegimeController,
    RegimeDecision,
    RegimeState,
    SynapticMemoryAdapter,
)
from .config import NeuroHybridFlags
from .contract_api import (
    NeuroContractMetadata,
    NeuroModuleAdapter,
    NeuroOutputPack,
    NeuroSignalPack,
)
from .contracts import (
    FUNCTIONAL_COVERAGE_MATRIX,
    NEURO_CONTRACTS,
    ContractSpec,
    FunctionalCoverageRecord,
)
from .prediction_error import BoundedUpdateResult, PredictorEMA, compute_delta, update_bounded

__all__ = [
    "ContractSpec",
    "FunctionalCoverageRecord",
    "FUNCTIONAL_COVERAGE_MATRIX",
    "NEURO_CONTRACTS",
    "NeuroContractMetadata",
    "NeuroHybridFlags",
    "NeuroModuleAdapter",
    "NeuroOutputPack",
    "NeuroSignalPack",
    "NeuroAIStepMetrics",
    "PredictionErrorAdapter",
    "PredictionErrorMetrics",
    "PredictorEMA",
    "BoundedUpdateResult",
    "compute_delta",
    "update_bounded",
    "RegimeController",
    "RegimeDecision",
    "RegimeState",
    "SynapticMemoryAdapter",
]
