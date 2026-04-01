"""
Unit Tests for QILM (Quantum-Inspired Long-term Memory)

Tests phase-entangled memory storage and retrieval.
"""

import numpy as np
import pytest

from mlsdm.memory.qilm_module import QILM


class TestQILMInitialization:
    """Test QILM initialization."""

    def test_initialization(self):
        """Test QILM can be initialized."""
        qilm = QILM()
        assert qilm is not None
        assert len(qilm.memory) == 0
        assert len(qilm.phases) == 0


class TestQILMEntanglePhase:
    """Test phase entanglement."""

    def test_entangle_phase_basic(self):
        """Test basic phase entanglement."""
        qilm = QILM()
        vector = np.array([1.0, 2.0, 3.0])
        phase = 0.5

        qilm.entangle_phase(vector, phase)

        assert len(qilm.memory) == 1
        assert len(qilm.phases) == 1
        assert qilm.phases[0] == 0.5
        np.testing.assert_array_almost_equal(qilm.memory[0], vector)

    def test_entangle_phase_without_phase(self):
        """Test entanglement with auto-generated phase."""
        qilm = QILM()
        vector = np.array([1.0, 2.0, 3.0])

        qilm.entangle_phase(vector)

        assert len(qilm.memory) == 1
        assert len(qilm.phases) == 1
        # Phase should be auto-generated (random)
        assert isinstance(qilm.phases[0], float)
        assert 0.0 <= qilm.phases[0] <= 1.0

    def test_entangle_phase_multiple_vectors(self):
        """Test entangling multiple vectors."""
        qilm = QILM()

        vectors = [np.array([1.0, 2.0]), np.array([3.0, 4.0]), np.array([5.0, 6.0])]
        phases = [0.1, 0.5, 0.9]

        for vec, phase in zip(vectors, phases, strict=False):
            qilm.entangle_phase(vec, phase)

        assert len(qilm.memory) == 3
        assert len(qilm.phases) == 3
        assert qilm.phases == phases

    def test_entangle_phase_invalid_type(self):
        """Test entanglement rejects invalid vector type."""
        qilm = QILM()

        with pytest.raises(TypeError, match="NumPy array"):
            qilm.entangle_phase([1, 2, 3], 0.5)

    def test_entangle_phase_converts_to_float(self):
        """Test entanglement converts vector to float."""
        qilm = QILM()
        vector = np.array([1, 2, 3], dtype=np.int32)

        qilm.entangle_phase(vector, 0.5)

        assert qilm.memory[0].dtype == np.float64


class TestQILMRetrieve:
    """Test phase-based retrieval."""

    def test_retrieve_exact_match(self):
        """Test retrieval with exact phase match."""
        qilm = QILM()

        vec1 = np.array([1.0, 2.0])
        vec2 = np.array([3.0, 4.0])
        vec3 = np.array([5.0, 6.0])

        qilm.entangle_phase(vec1, 0.1)
        qilm.entangle_phase(vec2, 0.5)
        qilm.entangle_phase(vec3, 0.9)

        # Retrieve phase 0.5
        results = qilm.retrieve(0.5, tolerance=0.0)

        assert len(results) == 1
        np.testing.assert_array_almost_equal(results[0], vec2)

    def test_retrieve_with_tolerance(self):
        """Test retrieval with phase tolerance."""
        qilm = QILM()

        vec1 = np.array([1.0, 2.0])
        vec2 = np.array([3.0, 4.0])
        vec3 = np.array([5.0, 6.0])

        qilm.entangle_phase(vec1, 0.1)
        qilm.entangle_phase(vec2, 0.15)
        qilm.entangle_phase(vec3, 0.9)

        # Retrieve with tolerance
        results = qilm.retrieve(0.1, tolerance=0.1)

        # Should get both vec1 and vec2
        assert len(results) == 2

    def test_retrieve_no_match(self):
        """Test retrieval with no matching phases."""
        qilm = QILM()

        vec1 = np.array([1.0, 2.0])
        qilm.entangle_phase(vec1, 0.1)

        results = qilm.retrieve(0.9, tolerance=0.0)

        assert len(results) == 0

    def test_retrieve_invalid_tolerance(self):
        """Test retrieve rejects negative tolerance."""
        qilm = QILM()

        with pytest.raises(ValueError, match="non-negative"):
            qilm.retrieve(0.5, tolerance=-0.1)

    def test_retrieve_non_numeric_phase(self):
        """Test retrieval with non-numeric phase."""
        qilm = QILM()

        vec1 = np.array([1.0, 2.0])
        vec2 = np.array([3.0, 4.0])

        # Entangle with string phases
        qilm.entangle_phase(vec1, "wake")
        qilm.entangle_phase(vec2, "sleep")

        # Retrieve with string phase
        results = qilm.retrieve("wake")

        assert len(results) == 1
        np.testing.assert_array_almost_equal(results[0], vec1)

    def test_retrieve_mixed_phase_types(self):
        """Test retrieval with mixed phase types."""
        qilm = QILM()

        vec1 = np.array([1.0, 2.0])
        vec2 = np.array([3.0, 4.0])
        vec3 = np.array([5.0, 6.0])

        qilm.entangle_phase(vec1, 0.5)
        qilm.entangle_phase(vec2, "custom")
        qilm.entangle_phase(vec3, 0.6)

        # Retrieve numeric phase
        results = qilm.retrieve(0.5, tolerance=0.2)

        # Should get vec1 and vec3, but not vec2 (different type)
        assert len(results) == 2


class TestQILMToDict:
    """Test QILM serialization."""

    def test_to_dict_empty(self):
        """Test serialization of empty QILM."""
        qilm = QILM()
        data = qilm.to_dict()

        assert isinstance(data, dict)
        assert "memory" in data
        assert "phases" in data
        assert data["memory"] == []
        assert data["phases"] == []

    def test_to_dict_with_data(self):
        """Test serialization with data."""
        qilm = QILM()

        vec1 = np.array([1.0, 2.0])
        vec2 = np.array([3.0, 4.0])

        qilm.entangle_phase(vec1, 0.1)
        qilm.entangle_phase(vec2, 0.9)

        data = qilm.to_dict()

        assert len(data["memory"]) == 2
        assert len(data["phases"]) == 2
        assert data["phases"] == [0.1, 0.9]
        assert data["memory"][0] == [1.0, 2.0]
        assert data["memory"][1] == [3.0, 4.0]

    def test_to_dict_preserves_phase_types(self):
        """Test serialization preserves different phase types."""
        qilm = QILM()

        vec1 = np.array([1.0])
        vec2 = np.array([2.0])

        qilm.entangle_phase(vec1, 0.5)
        qilm.entangle_phase(vec2, "custom_phase")

        data = qilm.to_dict()

        assert data["phases"] == [0.5, "custom_phase"]


class TestQILMIntegration:
    """Test QILM integration scenarios."""

    def test_store_and_retrieve_workflow(self):
        """Test complete store and retrieve workflow."""
        qilm = QILM()

        # Store multiple vectors with different phases
        wake_vectors = [np.array([i, i + 1]) for i in range(5)]
        sleep_vectors = [np.array([i + 10, i + 11]) for i in range(5)]

        for vec in wake_vectors:
            qilm.entangle_phase(vec, 0.1)

        for vec in sleep_vectors:
            qilm.entangle_phase(vec, 0.9)

        # Retrieve wake phase
        wake_results = qilm.retrieve(0.1, tolerance=0.0)
        assert len(wake_results) == 5

        # Retrieve sleep phase
        sleep_results = qilm.retrieve(0.9, tolerance=0.0)
        assert len(sleep_results) == 5

    def test_large_memory_storage(self):
        """Test storage and retrieval of many vectors."""
        qilm = QILM()

        # Store 100 vectors
        for i in range(100):
            vec = np.array([i, i + 1, i + 2])
            phase = i / 100.0
            qilm.entangle_phase(vec, phase)

        assert len(qilm.memory) == 100
        assert len(qilm.phases) == 100

        # Retrieve middle range
        results = qilm.retrieve(0.5, tolerance=0.05)
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
