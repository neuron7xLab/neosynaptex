"""State management subsystem for MLSDM.

This module provides schema-validated, versioned persistence for system state,
including memory stores and QILM data.

Public API Exports:
- SystemStateRecord: Pydantic model for validated system state
- MemoryStateRecord: Pydantic model for MultiLevelSynapticMemory state
- QILMStateRecord: Pydantic model for QILM state
- save_system_state: Save validated system state to file
- load_system_state: Load and validate system state from file
- delete_system_state: Delete system state file
- recover_system_state: Attempt recovery from corrupted state

Usage:
    from mlsdm.state import save_system_state, load_system_state

    # Save state
    save_system_state(state, "/path/to/state.json")

    # Load state with validation
    state = load_system_state("/path/to/state.json")
"""

from .system_state_schema import (
    MemoryStateRecord,
    QILMStateRecord,
    SystemStateRecord,
)
from .system_state_store import (
    delete_system_state,
    load_system_state,
    recover_system_state,
    save_system_state,
)

__all__ = [
    # Schema models
    "SystemStateRecord",
    "MemoryStateRecord",
    "QILMStateRecord",
    # Store operations
    "save_system_state",
    "load_system_state",
    "delete_system_state",
    "recover_system_state",
]
