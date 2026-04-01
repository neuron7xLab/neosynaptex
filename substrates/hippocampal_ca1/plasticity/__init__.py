"""
Plasticity Module for Hippocampal CA1

Implements synaptic plasticity mechanisms:
- Ca²⁺-based LTP/LTD (Graupner-Brunel model)
- Eligibility traces (BTSP)
- OLM-mediated plasticity gating
- Homeostatic regulation
- Unified weight matrix with STP and plasticity
"""

from .calcium_plasticity import (
    CalciumBasedSynapse,
    HomeostaticRegulator,
    OLMGate,
    SynapseState,
    compute_place_field_novelty,
)
from .unified_weights import (
    InputSource,
    UnifiedWeightMatrix,
    create_source_type_matrix,
)

__all__ = [
    "CalciumBasedSynapse",
    "HomeostaticRegulator",
    "OLMGate",
    "SynapseState",
    "compute_place_field_novelty",
    "InputSource",
    "UnifiedWeightMatrix",
    "create_source_type_matrix",
]
