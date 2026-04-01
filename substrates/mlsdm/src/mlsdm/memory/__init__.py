"""Memory subsystem for MLSDM.

This module provides the Phase-Entangled Lattice Memory (PELM) system,
a bounded phase-entangled lattice in classical embedding space for efficient
memory storage and retrieval with phase-based organization.

Public API Exports:
- PhaseEntangledLatticeMemory: Main class (canonical name)
- PELM: Convenient alias for PhaseEntangledLatticeMemory (recommended)
- MemoryRetrieval: Memory retrieval result dataclass
- QILM_v2: Deprecated alias for backward compatibility (use PELM or PhaseEntangledLatticeMemory instead)

Usage:
    # Recommended - use PELM alias:
    from mlsdm.memory import PELM
    memory = PELM(dimension=384, capacity=20000)

    # Or use full name:
    from mlsdm.memory import PhaseEntangledLatticeMemory
    memory = PhaseEntangledLatticeMemory(dimension=384, capacity=20000)

    # Deprecated (for backward compatibility only):
    from mlsdm.memory import QILM_v2  # Will be removed in v2.0.0
    memory = QILM_v2(dimension=384, capacity=20000)
"""

from .phase_entangled_lattice_memory import (
    MemoryRetrieval,
    PhaseEntangledLatticeMemory,
)

# Convenient alias (recommended for new code)
PELM = PhaseEntangledLatticeMemory

# Backward compatibility (DEPRECATED - will be removed in v2.0.0)
# Use PhaseEntangledLatticeMemory or PELM instead
QILM_v2 = PhaseEntangledLatticeMemory

__all__ = [
    "PhaseEntangledLatticeMemory",  # Canonical name
    "PELM",  # Convenient alias (recommended)
    "MemoryRetrieval",  # Dataclass for retrieval results
    "QILM_v2",  # Deprecated alias
]
