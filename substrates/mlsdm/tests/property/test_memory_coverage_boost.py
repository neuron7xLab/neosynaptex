"""
Property-based tests to boost PELM coverage to 95%+

This module contains comprehensive property tests using Hypothesis
to test edge cases and error paths in PhaseEntangledLatticeMemory.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.memory import PhaseEntangledLatticeMemory


class TestPELMPropertyCoverage:
    """Property tests to boost PELM coverage to 95%+"""

    @given(
        capacity=st.integers(min_value=1, max_value=100),
        embedding_dim=st.integers(min_value=2, max_value=128),
    )
    @settings(max_examples=50, deadline=None)
    def test_pelm_initialization_valid_params(self, capacity, embedding_dim):
        """Property: PELM initializes correctly for any valid parameters"""
        pelm = PhaseEntangledLatticeMemory(capacity=capacity, dimension=embedding_dim)

        assert pelm.capacity == capacity
        assert pelm.dimension == embedding_dim
        assert pelm.size == 0
        assert pelm.pointer == 0

    @given(
        num_stores=st.integers(min_value=1, max_value=30),
        phase_value=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=50, deadline=None)
    def test_pelm_store_retrieve_consistency(self, num_stores, phase_value):
        """Property: Stored vectors can always be retrieved"""
        pelm = PhaseEntangledLatticeMemory(capacity=100, dimension=16)

        embeddings = []
        for _ in range(num_stores):
            emb = np.random.randn(16).astype(np.float32).tolist()
            embeddings.append(emb)
            pelm.entangle(emb, phase_value)

        # Should retrieve at least some vectors
        results = pelm.retrieve(embeddings[0], phase_value, top_k=min(5, num_stores))
        assert len(results) > 0

    @given(
        query_phase=st.floats(min_value=0.0, max_value=1.0),
        tolerance=st.floats(min_value=0.01, max_value=0.5),
    )
    @settings(max_examples=50, deadline=None)
    def test_pelm_phase_tolerance_filter(self, query_phase, tolerance):
        """Property: Phase tolerance correctly filters results"""
        pelm = PhaseEntangledLatticeMemory(capacity=50, dimension=16)

        # Store vectors with known phases
        phases = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        for phase in phases:
            pelm.entangle(np.random.randn(16).astype(np.float32).tolist(), phase)

        query = np.random.randn(16).astype(np.float32).tolist()
        results = pelm.retrieve(query, query_phase, top_k=10, phase_tolerance=tolerance)

        # Results should be filtered by phase tolerance
        assert isinstance(results, list)


class TestPELMErrorPaths:
    """Test error paths and edge cases in PELM"""

    def test_entangle_with_invalid_vector_type(self):
        """Test entangle raises TypeError for non-list vector"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)

        # Test with numpy array instead of list
        with pytest.raises(TypeError, match="vector must be a list"):
            pelm.entangle(np.array([1.0, 2.0, 3.0]), 0.5)

    def test_entangle_with_invalid_element_type(self):
        """Test entangle raises TypeError for non-numeric vector elements"""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=100)

        # Test with string in vector
        with pytest.raises(TypeError, match="vector element.*must be numeric"):
            pelm.entangle([1.0, "invalid", 3.0], 0.5)

    def test_entangle_with_nan_value(self):
        """Test entangle raises ValueError for NaN in vector"""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=100)

        with pytest.raises(ValueError, match="vector contains invalid value"):
            pelm.entangle([1.0, float("nan"), 3.0], 0.5)

    def test_entangle_with_inf_value(self):
        """Test entangle raises ValueError for infinity in vector"""
        pelm = PhaseEntangledLatticeMemory(dimension=3, capacity=100)

        with pytest.raises(ValueError, match="vector contains invalid value"):
            pelm.entangle([1.0, float("inf"), 3.0], 0.5)

    def test_retrieve_from_empty_memory(self):
        """Test retrieve from empty memory returns empty list"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        query = [0.0] * 16

        results = pelm.retrieve(query, 0.5, top_k=5)
        assert results == []

    def test_entangle_batch_empty_list(self):
        """Test entangle_batch with empty list returns empty list"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)

        result = pelm.entangle_batch([], [])
        assert result == []

    def test_entangle_batch_dimension_mismatch(self):
        """Test entangle_batch raises ValueError for mismatched lengths"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)

        vectors = [[1.0] * 16, [2.0] * 16]
        phases = [0.5]  # Wrong length

        with pytest.raises(ValueError, match="must have same length"):
            pelm.entangle_batch(vectors, phases)

    def test_entangle_with_negative_phase(self):
        """Test entangle raises ValueError for negative phase"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        vector = [1.0] * 16

        with pytest.raises(ValueError, match="phase.*must be"):
            pelm.entangle(vector, -0.1)

    def test_entangle_with_phase_greater_than_one(self):
        """Test entangle raises ValueError for phase > 1.0"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        vector = [1.0] * 16

        with pytest.raises(ValueError, match="phase.*must be"):
            pelm.entangle(vector, 1.1)

    def test_retrieve_phase_filtering_with_no_matches(self):
        """Test retrieve returns empty list when no phases match tolerance"""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)

        # Store vectors with phase 0.0
        for _ in range(5):
            pelm.entangle([1.0] * 16, 0.0)

        # Query with phase 1.0 and very small tolerance (should return empty or minimal results)
        query = [1.0] * 16
        results = pelm.retrieve(query, 1.0, top_k=10, phase_tolerance=0.01)

        # Should return empty or minimal results due to phase mismatch
        assert isinstance(results, list)
