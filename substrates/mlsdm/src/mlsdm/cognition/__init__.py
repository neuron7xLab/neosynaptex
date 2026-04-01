"""Cognition module for MLSDM cognitive processing.

This module provides:
- Moral filtering (MoralFilter, MoralFilterV2)
- Ontology matching (OntologyMatcher)
- Synergy experience learning (SynergyExperienceMemory)
- Role & Boundary Controller (RoleBoundaryController)
"""

from mlsdm.cognition.moral_filter import MoralFilter
from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.cognition.ontology_matcher import OntologyMatcher
from mlsdm.cognition.role_boundary_controller import (
    BoundaryViolationType,
    Constraint,
    ExecutionStep,
    RoleBoundaryController,
    ScopeDefinition,
    StructuredTask,
    TaskPriority,
    TaskRequest,
)
from mlsdm.cognition.synergy_experience import (
    ComboStats,
    SynergyExperienceMemory,
    compute_eoi,
    create_state_signature,
)

__all__ = [
    "MoralFilter",
    "MoralFilterV2",
    "OntologyMatcher",
    "ComboStats",
    "SynergyExperienceMemory",
    "compute_eoi",
    "create_state_signature",
    "RoleBoundaryController",
    "TaskRequest",
    "StructuredTask",
    "Constraint",
    "ScopeDefinition",
    "ExecutionStep",
    "BoundaryViolationType",
    "TaskPriority",
]
