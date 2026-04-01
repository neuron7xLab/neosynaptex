"""Tests for __slots__ memory efficiency in TIER 1 memory components.

These tests verify that __slots__ are properly defined and provide memory efficiency
for memory-critical components (PELM, MultiLevelMemory, MemoryRetrieval).

Test Strategy:
- Verify __slots__ attribute exists
- Verify no __dict__ attribute (indicating __slots__ is working)
- Verify memory efficiency (objects with __slots__ use less memory)
"""

import sys
from datetime import datetime

import numpy as np

from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.memory.phase_entangled_lattice_memory import (
    MemoryRetrieval,
    PhaseEntangledLatticeMemory,
)
from mlsdm.memory.provenance import MemoryProvenance, MemorySource


class TestMemoryRetrievalSlots:
    """Test __slots__ for MemoryRetrieval dataclass."""

    def test_memory_retrieval_has_slots(self):
        """Verify MemoryRetrieval has __slots__ defined."""
        # This will fail before adding __slots__ to MemoryRetrieval
        assert hasattr(MemoryRetrieval, "__slots__"), (
            "MemoryRetrieval must define __slots__ for memory efficiency"
        )

    def test_memory_retrieval_no_dict(self):
        """Verify MemoryRetrieval instances don't have __dict__."""
        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        prov = MemoryProvenance(source=MemorySource.SYSTEM_PROMPT, confidence=1.0, timestamp=datetime.now())
        mem = MemoryRetrieval(
            vector=vec,
            phase=0.1,
            resonance=0.95,
            provenance=prov,
            memory_id="test-id"
        )

        # This will fail before adding __slots__
        assert not hasattr(mem, "__dict__"), (
            "MemoryRetrieval instances should not have __dict__ when __slots__ is used"
        )

    def test_memory_retrieval_memory_efficiency(self):
        """Verify MemoryRetrieval with __slots__ uses less memory."""
        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        prov = MemoryProvenance(source=MemorySource.SYSTEM_PROMPT, confidence=1.0, timestamp=datetime.now())
        mem = MemoryRetrieval(
            vector=vec,
            phase=0.1,
            resonance=0.95,
            provenance=prov,
            memory_id="test-id"
        )

        # Calculate size (excluding numpy array which dominates)
        # With __slots__, size should be smaller
        size = sys.getsizeof(mem)

        # Rough heuristic: with __slots__, object size should be < 200 bytes
        # (actual size depends on Python implementation, but dict overhead is ~200+ bytes)
        # This is a smoke test, not exact measurement
        assert size < 300, (
            f"MemoryRetrieval size ({size} bytes) suggests __dict__ overhead. "
            "Expected < 300 bytes with __slots__."
        )


class TestPhaseEntangledLatticeMemorySlots:
    """Test __slots__ for PhaseEntangledLatticeMemory."""

    def test_pelm_has_slots(self):
        """Verify PELM has __slots__ defined."""
        # This will fail before adding __slots__ to PELM
        assert hasattr(PhaseEntangledLatticeMemory, "__slots__"), (
            "PhaseEntangledLatticeMemory must define __slots__ for memory efficiency"
        )

    def test_pelm_no_dict(self):
        """Verify PELM instances don't have __dict__."""
        pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=100)

        # This will fail before adding __slots__
        assert not hasattr(pelm, "__dict__"), (
            "PhaseEntangledLatticeMemory instances should not have __dict__ when __slots__ is used"
        )

    def test_pelm_attributes_accessible(self):
        """Verify PELM attributes are still accessible with __slots__."""
        pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=100)

        # Verify core attributes work
        assert pelm.dimension == 384
        assert pelm.capacity == 100
        assert pelm.pointer == 0
        assert pelm.size == 0
        assert isinstance(pelm.memory_bank, np.ndarray)


class TestMultiLevelSynapticMemorySlots:
    """Test __slots__ for MultiLevelSynapticMemory."""

    def test_multilevel_has_slots(self):
        """Verify MultiLevelSynapticMemory has __slots__ defined."""
        # This will fail before adding __slots__ to MultiLevelSynapticMemory
        assert hasattr(MultiLevelSynapticMemory, "__slots__"), (
            "MultiLevelSynapticMemory must define __slots__ for memory efficiency"
        )

    def test_multilevel_no_dict(self):
        """Verify MultiLevelSynapticMemory instances don't have __dict__."""
        mem = MultiLevelSynapticMemory(dimension=384)

        # This will fail before adding __slots__
        assert not hasattr(mem, "__dict__"), (
            "MultiLevelSynapticMemory instances should not have __dict__ when __slots__ is used"
        )

    def test_multilevel_attributes_accessible(self):
        """Verify MultiLevelSynapticMemory attributes are still accessible with __slots__."""
        mem = MultiLevelSynapticMemory(dimension=384)

        # Verify core attributes work
        assert mem.dim == 384
        assert isinstance(mem.l1, np.ndarray)
        assert isinstance(mem.l2, np.ndarray)
        assert isinstance(mem.l3, np.ndarray)
        assert mem.lambda_l1 > 0
        assert mem.lambda_l2 > 0
        assert mem.lambda_l3 > 0
