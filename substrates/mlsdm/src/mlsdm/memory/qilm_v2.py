"""
DEPRECATED: This module has been renamed to phase_entangled_lattice_memory.

This file is kept for backward compatibility with code that imports directly from
mlsdm.memory.qilm_v2. Please update your imports to use:
    from mlsdm.memory import PhaseEntangledLatticeMemory, MemoryRetrieval
or
    from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory, MemoryRetrieval

This module will be removed in v2.0.0.
"""

# Re-export from the new module for backward compatibility
from .phase_entangled_lattice_memory import (
    MemoryRetrieval,
    PhaseEntangledLatticeMemory,
)

# Deprecated alias
QILM_v2 = PhaseEntangledLatticeMemory

__all__ = [
    "MemoryRetrieval",
    "QILM_v2",
    "PhaseEntangledLatticeMemory",
]
