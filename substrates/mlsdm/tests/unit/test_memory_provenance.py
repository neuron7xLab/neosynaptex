"""Unit tests for Memory Provenance System.

Tests the AI safety features for tracking memory origin and confidence
to prevent hallucination propagation in PELM.

Resolves: TD-003 (HIGH priority - AI Safety critical)
"""

from datetime import datetime

import numpy as np
import pytest

from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory
from mlsdm.memory.provenance import (
    MemoryProvenance,
    MemoryProvenanceError,
    MemorySource,
    enforce_provenance_integrity,
)
from mlsdm.memory.store import compute_content_hash


class TestMemoryProvenanceDataModel:
    """Test the provenance data model."""

    def test_provenance_creation(self):
        """Test creating a MemoryProvenance instance."""
        prov = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.95,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("test"),
        )

        assert prov.source == MemorySource.USER_INPUT
        assert prov.confidence == 0.95
        assert prov.llm_model is None
        assert prov.parent_id is None
        assert prov.content_hash is not None
        assert prov.lineage_hash is not None

    def test_provenance_confidence_validation(self):
        """Test confidence must be in [0.0, 1.0] range."""
        # Valid confidence values
        MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.0,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("zero"),
        )
        MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=1.0,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("one"),
        )

        # Invalid confidence values
        with pytest.raises(ValueError, match="Confidence must be in range"):
            MemoryProvenance(
                source=MemorySource.USER_INPUT,
                confidence=1.5,
                timestamp=datetime.now(),
                content_hash=compute_content_hash("bad"),
            )

        with pytest.raises(ValueError, match="Confidence must be in range"):
            MemoryProvenance(
                source=MemorySource.USER_INPUT,
                confidence=-0.1,
                timestamp=datetime.now(),
                content_hash=compute_content_hash("bad"),
            )

    def test_is_high_confidence_property(self):
        """Test is_high_confidence property."""
        high_conf = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.8,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("high"),
        )
        assert high_conf.is_high_confidence is True

        low_conf = MemoryProvenance(
            source=MemorySource.LLM_GENERATION,
            confidence=0.5,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("low"),
        )
        assert low_conf.is_high_confidence is False

    def test_is_llm_generated_property(self):
        """Test is_llm_generated property."""
        llm_prov = MemoryProvenance(
            source=MemorySource.LLM_GENERATION,
            confidence=0.6,
            timestamp=datetime.now(),
            llm_model="gpt-4",
            content_hash=compute_content_hash("llm"),
        )
        assert llm_prov.is_llm_generated is True

        user_prov = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.9,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("user"),
        )
        assert user_prov.is_llm_generated is False
        assert user_prov.lineage_hash is not None
        user_prov.verify_integrity()

    def test_lineage_hash_mismatch_raises(self):
        """Lineage hash mismatch should raise an error."""
        with pytest.raises(MemoryProvenanceError, match="lineage hash mismatch"):
            MemoryProvenance(
                source=MemorySource.USER_INPUT,
                confidence=0.9,
                timestamp=datetime.now(),
                content_hash=compute_content_hash("tamper"),
                lineage_hash="deadbeef",
            )

    def test_verify_integrity_detects_tampering(self):
        """verify_integrity should fail if fields are mutated."""
        prov = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.9,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("safe"),
        )

        object.__setattr__(prov, "content_hash", compute_content_hash("tampered"))

        with pytest.raises(MemoryProvenanceError, match="integrity check failed"):
            prov.verify_integrity()

    def test_enforce_provenance_rejects_content_hash_mismatch(self):
        """enforce_provenance_integrity rejects mismatched content hashes."""
        content = "content mismatch"
        prov = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.9,
            timestamp=datetime.now(),
            content_hash=compute_content_hash(content),
        )

        with pytest.raises(MemoryProvenanceError, match="content hash mismatch"):
            enforce_provenance_integrity(
                prov,
                content_hash=compute_content_hash("other"),
            )

    def test_enforce_provenance_rejects_policy_hash_mismatch(self):
        """enforce_provenance_integrity rejects mismatched policy hashes."""
        content = "policy mismatch"
        prov = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.9,
            timestamp=datetime.now(),
            content_hash=compute_content_hash(content),
            policy_hash="policy-a",
        )

        with pytest.raises(MemoryProvenanceError, match="policy hash mismatch"):
            enforce_provenance_integrity(
                prov,
                content_hash=compute_content_hash(content),
                policy_hash="policy-b",
            )

    def test_enforce_provenance_rejects_contract_version_mismatch(self):
        """enforce_provenance_integrity rejects mismatched contract versions."""
        content = "contract mismatch"
        prov = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.9,
            timestamp=datetime.now(),
            content_hash=compute_content_hash(content),
            policy_contract_version="1.0",
        )

        with pytest.raises(MemoryProvenanceError, match="policy contract version mismatch"):
            enforce_provenance_integrity(
                prov,
                content_hash=compute_content_hash(content),
                policy_contract_version="2.0",
            )


class TestPELMProvenanceStorage:
    """Test PELM provenance storage capabilities."""

    def test_store_with_high_confidence(self):
        """High confidence memories should be stored successfully."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vector = np.random.randn(16).astype(np.float32).tolist()
        provenance = MemoryProvenance(
            source=MemorySource.USER_INPUT, confidence=0.9, timestamp=datetime.now()
        )

        idx = pelm.entangle(vector, phase=0.5, provenance=provenance)

        assert idx >= 0  # Successfully stored (not -1)
        assert pelm.size == 1
        assert len(pelm._provenance) == 1
        assert pelm._provenance[0].confidence == 0.9

    def test_reject_low_confidence(self):
        """Low confidence memories should be rejected."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)
        pelm._confidence_threshold = 0.5

        vector = np.random.randn(16).astype(np.float32).tolist()
        provenance = MemoryProvenance(
            source=MemorySource.LLM_GENERATION,
            confidence=0.3,  # Below threshold
            timestamp=datetime.now(),
        )

        idx = pelm.entangle(vector, phase=0.5, provenance=provenance)

        assert idx == -1  # Rejected
        assert pelm.size == 0

    def test_default_provenance_when_none(self):
        """When no provenance provided, should use system default."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vector = np.random.randn(16).astype(np.float32).tolist()
        idx = pelm.entangle(vector, phase=0.5)  # No provenance

        assert idx >= 0
        assert pelm.size == 1
        assert len(pelm._provenance) == 1
        assert pelm._provenance[0].source == MemorySource.SYSTEM_PROMPT
        assert pelm._provenance[0].confidence == 1.0


class TestPELMProvenanceRetrieval:
    """Test PELM retrieval with confidence filtering."""

    def test_retrieve_filters_by_confidence(self):
        """Retrieval should filter out low-confidence memories."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)
        # Lower the threshold so both can be stored
        pelm._confidence_threshold = 0.3

        # Store high confidence memory
        vector_high = np.random.randn(16).astype(np.float32).tolist()
        pelm.entangle(
            vector_high,
            phase=0.5,
            provenance=MemoryProvenance(
                source=MemorySource.USER_INPUT, confidence=0.9, timestamp=datetime.now()
            ),
        )

        # Store low confidence memory
        vector_low = np.random.randn(16).astype(np.float32).tolist()
        pelm.entangle(
            vector_low,
            phase=0.5,
            provenance=MemoryProvenance(
                source=MemorySource.LLM_GENERATION, confidence=0.4, timestamp=datetime.now()
            ),
        )

        assert pelm.size == 2  # Both stored

        # Retrieve with min_confidence=0.5 (should filter out 0.4)
        query = np.random.randn(16).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5, top_k=10, min_confidence=0.5)

        # Only high-confidence memory should be returned
        assert len(results) == 1
        assert results[0].provenance.confidence >= 0.5

    def test_retrieve_returns_provenance(self):
        """Retrieved memories should include provenance metadata."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vector = np.random.randn(16).astype(np.float32).tolist()
        provenance = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.95,
            timestamp=datetime.now(),
            llm_model=None,
        )

        pelm.entangle(vector, phase=0.5, provenance=provenance)

        query = np.random.randn(16).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5, top_k=1)

        assert len(results) == 1
        assert hasattr(results[0], "provenance")
        assert hasattr(results[0], "memory_id")
        assert results[0].provenance.source == MemorySource.USER_INPUT
        assert results[0].provenance.confidence == 0.95

    def test_retrieve_with_zero_min_confidence(self):
        """With min_confidence=0.0, all memories should be retrieved."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)
        # Lower threshold to allow all to be stored
        pelm._confidence_threshold = 0.0

        # Store memories with varying confidence
        for conf in [0.3, 0.5, 0.9]:
            vector = np.random.randn(16).astype(np.float32).tolist()
            pelm.entangle(
                vector,
                phase=0.5,
                provenance=MemoryProvenance(
                    source=MemorySource.USER_INPUT, confidence=conf, timestamp=datetime.now()
                ),
            )

        query = np.random.randn(16).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5, top_k=10, min_confidence=0.0)

        # All memories should be returned (subject to phase tolerance)
        assert len(results) == 3


class TestPELMConfidenceBasedEviction:
    """Test confidence-based eviction when PELM reaches capacity."""

    def test_evict_lowest_confidence(self):
        """When full, should evict the lowest confidence memory."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=3)

        # Fill to capacity with varying confidence
        confidences = [0.9, 0.7, 0.5]
        for conf in confidences:
            vector = np.random.randn(16).astype(np.float32).tolist()
            pelm.entangle(
                vector,
                phase=0.5,
                provenance=MemoryProvenance(
                    source=MemorySource.USER_INPUT, confidence=conf, timestamp=datetime.now()
                ),
            )

        assert pelm.size == 3

        # Store one more with high confidence (should evict 0.5)
        vector_new = np.random.randn(16).astype(np.float32).tolist()
        pelm.entangle(
            vector_new,
            phase=0.5,
            provenance=MemoryProvenance(
                source=MemorySource.USER_INPUT, confidence=0.8, timestamp=datetime.now()
            ),
        )

        # Size should still be 3 (one was evicted)
        assert pelm.size == 3

        # Lowest confidence (0.5) should be gone
        remaining_confidences = [p.confidence for p in pelm._provenance[: pelm.size]]
        assert 0.5 not in remaining_confidences
        assert min(remaining_confidences) >= 0.7

    def test_eviction_maintains_consistency(self):
        """Eviction should maintain consistency across all arrays."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=2)

        # Fill capacity
        for i in range(2):
            vector = np.random.randn(16).astype(np.float32).tolist()
            pelm.entangle(
                vector,
                phase=0.5,
                provenance=MemoryProvenance(
                    source=MemorySource.USER_INPUT,
                    confidence=0.5 + i * 0.2,  # 0.5, 0.7
                    timestamp=datetime.now(),
                ),
            )

        # Add one more (should evict first with confidence 0.5)
        vector_new = np.random.randn(16).astype(np.float32).tolist()
        pelm.entangle(
            vector_new,
            phase=0.5,
            provenance=MemoryProvenance(
                source=MemorySource.USER_INPUT, confidence=0.9, timestamp=datetime.now()
            ),
        )

        # Verify consistency
        assert pelm.size == 2
        assert len(pelm._provenance) == 2
        assert len(pelm._memory_ids) == 2

        # Verify retrieval still works
        query = np.random.randn(16).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5, top_k=10)
        assert len(results) <= 2


class TestPELMBatchProvenance:
    """Test batch operations with provenance."""

    def test_entangle_batch_with_provenance(self):
        """Batch entangle should support provenance."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vectors = [np.random.randn(16).astype(np.float32).tolist() for _ in range(3)]
        phases = [0.5, 0.5, 0.5]
        provenances = [
            MemoryProvenance(
                source=MemorySource.USER_INPUT, confidence=0.9, timestamp=datetime.now()
            )
            for _ in range(3)
        ]

        indices = pelm.entangle_batch(vectors, phases, provenances=provenances)

        assert len(indices) == 3
        assert all(idx >= 0 for idx in indices)
        assert pelm.size == 3
        assert all(p.confidence == 0.9 for p in pelm._provenance[: pelm.size])

    def test_entangle_batch_rejects_low_confidence(self):
        """Batch entangle should reject low confidence memories."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)
        pelm._confidence_threshold = 0.5

        vectors = [np.random.randn(16).astype(np.float32).tolist() for _ in range(3)]
        phases = [0.5, 0.5, 0.5]
        provenances = [
            MemoryProvenance(
                source=MemorySource.USER_INPUT, confidence=conf, timestamp=datetime.now()
            )
            for conf in [0.9, 0.3, 0.7]  # Middle one below threshold
        ]

        indices = pelm.entangle_batch(vectors, phases, provenances=provenances)

        assert len(indices) == 3
        assert indices[0] >= 0  # Accepted
        assert indices[1] == -1  # Rejected
        assert indices[2] >= 0  # Accepted
        assert pelm.size == 2  # Only 2 stored

    def test_entangle_batch_without_provenance(self):
        """Batch entangle should work without provenance (backward compat)."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vectors = [np.random.randn(16).astype(np.float32).tolist() for _ in range(2)]
        phases = [0.5, 0.5]

        indices = pelm.entangle_batch(vectors, phases)

        assert len(indices) == 2
        assert all(idx >= 0 for idx in indices)
        assert pelm.size == 2
        # Should have default system provenance
        assert all(p.source == MemorySource.SYSTEM_PROMPT for p in pelm._provenance[: pelm.size])


class TestBackwardCompatibility:
    """Test backward compatibility with existing PELM usage."""

    def test_entangle_without_provenance_still_works(self):
        """Existing code without provenance parameter should still work."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vector = np.random.randn(16).astype(np.float32).tolist()
        idx = pelm.entangle(vector, phase=0.5)

        assert idx >= 0
        assert pelm.size == 1

    def test_retrieve_without_min_confidence_still_works(self):
        """Existing retrieval code should work with default min_confidence=0.0."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=10)

        vector = np.random.randn(16).astype(np.float32).tolist()
        pelm.entangle(vector, phase=0.5)

        query = np.random.randn(16).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5)

        assert len(results) >= 0  # Should work
        # Results should include provenance fields
        if len(results) > 0:
            assert hasattr(results[0], "provenance")
            assert hasattr(results[0], "memory_id")
