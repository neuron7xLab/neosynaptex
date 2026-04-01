"""Schema definitions for MLSDM system state persistence.

This module defines Pydantic models for validating system state data.
All persisted state goes through these schemas to ensure integrity
and enable migrations.

Invariants:
- version: monotonically increasing schema version (currently 1)
- created_at <= updated_at for all records
- dimension > 0 for memory records
- all decay rates (lambda_*) in (0, 1]
- all thresholds (theta_*) > 0
- all gating factors in [0, 1]
- state arrays match declared dimension
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# Current schema version - increment when schema changes
CURRENT_SCHEMA_VERSION = 1


class MemoryStateRecord(BaseModel):
    """Schema for MultiLevelSynapticMemory state.

    Invariants:
    - dimension > 0
    - all lambda values in (0, 1]
    - all theta values > 0
    - all gating values in [0, 1]
    - state array lengths == dimension
    """

    model_config = ConfigDict(populate_by_name=True)

    dimension: int = Field(..., gt=0, description="Vector dimension")
    lambda_l1: float = Field(..., gt=0, le=1, description="L1 decay rate")
    lambda_l2: float = Field(..., gt=0, le=1, description="L2 decay rate")
    lambda_l3: float = Field(..., gt=0, le=1, description="L3 decay rate")
    theta_l1: float = Field(..., gt=0, description="L1→L2 consolidation threshold")
    theta_l2: float = Field(..., gt=0, description="L2→L3 consolidation threshold")
    gating12: float = Field(..., ge=0, le=1, description="L1→L2 gating factor")
    gating23: float = Field(..., ge=0, le=1, description="L2→L3 gating factor")
    state_l1: list[float] = Field(..., alias="state_L1", description="L1 memory state vector")
    state_l2: list[float] = Field(..., alias="state_L2", description="L2 memory state vector")
    state_l3: list[float] = Field(..., alias="state_L3", description="L3 memory state vector")

    @model_validator(mode="after")
    def validate_state_dimensions(self) -> MemoryStateRecord:
        """Validate that state arrays match declared dimension."""
        if len(self.state_l1) != self.dimension:
            raise ValueError(
                f"state_L1 length ({len(self.state_l1)}) != dimension ({self.dimension})"
            )
        if len(self.state_l2) != self.dimension:
            raise ValueError(
                f"state_L2 length ({len(self.state_l2)}) != dimension ({self.dimension})"
            )
        if len(self.state_l3) != self.dimension:
            raise ValueError(
                f"state_L3 length ({len(self.state_l3)}) != dimension ({self.dimension})"
            )
        return self


class QILMStateRecord(BaseModel):
    """Schema for QILM (Quantum-Inspired Lattice Memory) state.

    Invariants:
    - memory and phases arrays have matching lengths
    - phase values are numeric
    """

    memory: list[list[float]] = Field(..., description="Memory vectors")
    phases: list[float] = Field(..., description="Phase values for each vector")

    @model_validator(mode="after")
    def validate_lengths_match(self) -> QILMStateRecord:
        """Validate that memory and phases arrays have matching lengths."""
        if len(self.memory) != len(self.phases):
            raise ValueError(
                f"memory length ({len(self.memory)}) != phases length ({len(self.phases)})"
            )
        return self


class SystemStateRecord(BaseModel):
    """Schema for complete system state.

    This is the top-level model for persisted system state.

    Invariants:
    - version >= 1 (schema version)
    - created_at <= updated_at
    - id is non-empty if provided
    """

    version: int = Field(
        default=CURRENT_SCHEMA_VERSION,
        ge=1,
        description="Schema version for migrations",
    )
    id: str | None = Field(default=None, description="Optional unique state identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when state was first created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when state was last updated",
    )
    memory_state: MemoryStateRecord = Field(..., description="MultiLevelSynapticMemory state")
    qilm: QILMStateRecord = Field(..., description="QILM state")

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, v: str | None) -> str | None:
        """Validate that id is not an empty string if provided."""
        if v is not None and v.strip() == "":
            raise ValueError("id cannot be an empty string")
        return v

    @model_validator(mode="after")
    def validate_timestamps(self) -> SystemStateRecord:
        """Validate that created_at <= updated_at."""
        if self.created_at > self.updated_at:
            raise ValueError(f"created_at ({self.created_at}) > updated_at ({self.updated_at})")
        return self


def create_system_state_from_dict(data: dict[str, Any]) -> SystemStateRecord:
    """Create a SystemStateRecord from a dictionary.

    This function handles the conversion from the legacy format used by
    MemoryManager.save_system_state() to the new validated schema.

    Args:
        data: Dictionary containing state data (legacy or new format)

    Returns:
        Validated SystemStateRecord

    Raises:
        ValueError: If data is invalid or cannot be converted
    """
    # Check if this is already in the new format
    if "version" in data and "memory_state" in data and "qilm" in data:
        return SystemStateRecord.model_validate(data)

    # Convert from legacy format
    memory_data = data.get("memory_state", {})
    qilm_data = data.get("qilm", {})

    if not memory_data or not qilm_data:
        raise ValueError("Missing required state data: memory_state and qilm")

    # Build new format
    new_data = {
        "version": CURRENT_SCHEMA_VERSION,
        "memory_state": memory_data,
        "qilm": qilm_data,
    }

    return SystemStateRecord.model_validate(new_data)


def validate_state_integrity(state: SystemStateRecord) -> list[str]:
    """Validate additional integrity constraints on a state record.

    This performs deeper validation beyond Pydantic's field validators,
    checking cross-field relationships and business rules.

    Args:
        state: State record to validate

    Returns:
        List of warning messages (empty if all valid)
    """
    warnings: list[str] = []

    # Check memory dimensions are consistent
    memory = state.memory_state
    if memory.dimension <= 0:
        warnings.append(f"Invalid memory dimension: {memory.dimension}")

    # Check for potential numerical issues in state vectors
    for i, val in enumerate(memory.state_l1):
        if abs(val) > 1e10:
            warnings.append(f"L1 value at index {i} is very large: {val}")

    for i, val in enumerate(memory.state_l2):
        if abs(val) > 1e10:
            warnings.append(f"L2 value at index {i} is very large: {val}")

    for i, val in enumerate(memory.state_l3):
        if abs(val) > 1e10:
            warnings.append(f"L3 value at index {i} is very large: {val}")

    # Check QILM consistency
    qilm = state.qilm
    for i, vec in enumerate(qilm.memory):
        if len(vec) == 0:
            warnings.append(f"QILM memory vector at index {i} is empty")

    return warnings
